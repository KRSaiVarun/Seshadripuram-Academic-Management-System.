/**
 * ============================================================================
 * Seshadripuram College - Smart Academic Management System
 * SECTION 16: Cosmic Rocket Cursor & High-Performance Particle Engine
 * 
 * Features:
 *  - High-performance HTML5 Canvas particle system with true Object Pooling
 *  - Enforced global MAX_PARTICLES ceiling across all particle types
 *  - Frame-rate independent physics (delta-time, shortest-arc angular lerp)
 *  - Authentic ROCKET_SPEED displacement clamping and ENGINE_GLOW scaling
 *  - Adaptive Performance Monitoring (High / Medium / Low / Minimal quality tiers)
 *  - Full Accessibility & prefers-reduced-motion compliance
 *  - Event isolation (UI controls do not trigger spurious background fireworks)
 *  - Dual Pointer-Events support (Mouse/Pen custom cursor, Touch touch-bursts)
 * ============================================================================
 */

(function (root, factory) {
  if (typeof define === 'function' && define.amd) {
    define([], factory);
  } else if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.CosmicEngine = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  // --------------------------------------------------------------------------
  // 1. CONFIGURATION TOKENS
  // --------------------------------------------------------------------------
  const CONFIG = {
    // Rocket Aerodynamics & Speed Limits
    ROCKET_SMOOTHING: 0.14,      // Positional interpolation factor per 60fps frame
    ROCKET_SPEED: 22.0,          // Maximum travel displacement clamp (px/frame)
    ROTATION_SMOOTHING: 0.16,    // Angular interpolation factor
    BANKING_FACTOR: 0.35,        // Roll compression factor during sharp turns
    RESTING_ANGLE: 0,            // Resting angle (0 rad = facing upright)
    RESTING_TIMEOUT: 550,        // Milliseconds stationary before returning upright

    // Smoke Trail Physics
    SMOKE_RATE: 1.0,             // Smoke emission factor
    SMOKE_LIFETIME: 0.95,        // Seconds before vapor fully dissipates
    SMOKE_SPEED_MIN: 15.0,       // Ejection velocity min (px/s)
    SMOKE_SPEED_MAX: 45.0,       // Ejection velocity max (px/s)
    SMOKE_EXPANSION: 28.0,       // Max vapor puff radius (px)

    // Fireworks & Explosions
    FIREWORK_PARTICLES: 75,      // Sparks per standard burst
    FIREWORK_GRAVITY: 160.0,     // Downward gravity acceleration (px/s^2)
    PARTICLE_FRICTION: 0.965,    // Air drag decay multiplier per 60fps frame
    PARTICLE_DECAY: 0.85,        // Spark lifetime in seconds
    SHAKE_DECAY: 0.91,           // Screen shake decay per 60fps frame

    // Global Limits & Visual Multipliers
    MAX_PARTICLES: 1200,         // Absolute global active particle ceiling
    ENGINE_GLOW: 1.0,            // Multiplier for engine plume & bloom brightness
    STAR_COUNT: 160,             // Number of twinkling background stars

    // Feature Toggles
    ENABLE_SMOKE: true,
    ENABLE_SHAKE: true,
    ENABLE_STARS: true,
    ENABLE_CUSTOM_CURSOR: true
  };

  // Curated cosmic palettes matching Seshadripuram Section 16 master design
  const PALETTES = [
    { name: 'Sapphire', colors: ['#00E5FF', '#087BFF', '#7900FF', '#FFFFFF', '#D500F9'] },
    { name: 'Supernova', colors: ['#FFD700', '#FF8A00', '#FF2DAA', '#FFFFFF', '#FF1744'] },
    { name: 'Emerald', colors: ['#00F5D4', '#00D084', '#00B4D8', '#FFFFFF', '#76FF03'] },
    { name: 'Cyberpunk', colors: ['#D500F9', '#7900FF', '#00E5FF', '#FFD700', '#FF007F'] }
  ];

  // --------------------------------------------------------------------------
  // 2. TRUE PARTICLE POOL ARCHITECTURE
  // --------------------------------------------------------------------------
  class ParticlePool {
    constructor(maxCapacity) {
      this.capacity = maxCapacity;
      this.pool = new Array(maxCapacity);
      for (let i = 0; i < maxCapacity; i++) {
        this.pool[i] = {
          active: false,
          type: 'spark', // 'smoke' | 'spark' | 'flare' | 'shockwave'
          x: 0, y: 0, prevX: 0, prevY: 0,
          vx: 0, vy: 0,
          radius: 0, maxRadius: 0, size: 0,
          life: 0, maxLife: 0,
          rotation: 0, rotSpeed: 0,
          color: '#FFFFFF',
          alpha: 1.0, baseAlpha: 1.0,
          isTwinkle: false, twinkleSpeed: 0,
          isSecondaryBurst: false, hasBurst: false
        };
      }
      this.activeList = [];
    }

    obtain(type) {
      if (this.activeList.length >= this.capacity) {
        return null; // Global ceiling enforced strictly
      }
      for (let i = 0; i < this.capacity; i++) {
        const p = this.pool[i];
        if (!p.active) {
          p.active = true;
          p.type = type;
          p.life = 0;
          p.hasBurst = false;
          this.activeList.push(p);
          return p;
        }
      }
      return null;
    }

    releaseAt(activeIndex) {
      const p = this.activeList[activeIndex];
      p.active = false;
      // Fast swap-and-pop to avoid array shifting allocations
      const last = this.activeList.pop();
      if (activeIndex < this.activeList.length) {
        this.activeList[activeIndex] = last;
      }
    }

    clear() {
      for (let i = 0; i < this.activeList.length; i++) {
        this.activeList[i].active = false;
      }
      this.activeList.length = 0;
    }

    get count() {
      return this.activeList.length;
    }
  }

  // --------------------------------------------------------------------------
  // 3. ENGINE STATE & ADAPTIVE PERFORMANCE MONITOR
  // --------------------------------------------------------------------------
  let canvas = null;
  let ctx = null;
  let shakeContainer = null;
  let pool = null;

  let viewportWidth = window.innerWidth;
  let viewportHeight = window.innerHeight;
  let dpr = 1;

  let animFrameId = null;
  let lastTimestamp = performance.now();
  let accumulatedSmoke = 0;
  let shakeIntensity = 0;

  // Starfield
  let stars = [];

  // Rocket State
  const rocket = {
    x: viewportWidth * 0.5,
    y: viewportHeight * 0.5,
    targetX: viewportWidth * 0.5,
    targetY: viewportHeight * 0.5,
    vx: 0,
    vy: 0,
    speed: 0,
    angle: 0,
    targetAngle: 0,
    angularVelocity: 0,
    banking: 0,
    engineThrust: 0,
    lastMoveTime: performance.now(),
    isActive: false,
    isFinePointer: true,
    isPointerDown: false,
    pointerDownTime: 0
  };

  // Performance Quality Levels: High, Medium, Low, Minimal
  const PERFORMANCE = {
    fps: 60,
    frameTime: 16.6,
    quality: 'High', // 'High' | 'Medium' | 'Low' | 'Minimal'
    qualityScale: 1.0,
    frameCount: 0,
    lastMeasureTime: performance.now(),
    fpsHistory: []
  };

  // Accessibility Reduced Motion
  let isReducedMotion = false;

  // --------------------------------------------------------------------------
  // 4. PERFORMANCE MEASUREMENT & QUALITY ADAPTATION
  // --------------------------------------------------------------------------
  function updatePerformance(dt, currentTimestamp) {
    PERFORMANCE.frameCount++;
    const elapsed = currentTimestamp - PERFORMANCE.lastMeasureTime;

    if (elapsed >= 500) {
      const currentFps = Math.round((PERFORMANCE.frameCount * 1000) / elapsed);
      PERFORMANCE.fps = currentFps;
      PERFORMANCE.frameTime = Number((elapsed / PERFORMANCE.frameCount).toFixed(1));
      PERFORMANCE.frameCount = 0;
      PERFORMANCE.lastMeasureTime = currentTimestamp;

      PERFORMANCE.fpsHistory.push(currentFps);
      if (PERFORMANCE.fpsHistory.length > 6) PERFORMANCE.fpsHistory.shift();

      const avgFps = PERFORMANCE.fpsHistory.reduce((a, b) => a + b, 0) / PERFORMANCE.fpsHistory.length;

      // Adapt quality tier dynamically if performance drops
      if (avgFps < 28 && PERFORMANCE.quality !== 'Minimal') {
        setQualityLevel('Minimal');
      } else if (avgFps < 42 && avgFps >= 28 && PERFORMANCE.quality !== 'Low') {
        setQualityLevel('Low');
      } else if (avgFps < 52 && avgFps >= 42 && PERFORMANCE.quality !== 'Medium') {
        setQualityLevel('Medium');
      } else if (avgFps >= 55 && PERFORMANCE.quality !== 'High') {
        setQualityLevel('High');
      }

      // Update telemetry badge if present in DOM
      const fpsBadge = document.getElementById('cosmic-fps-display');
      if (fpsBadge) {
        fpsBadge.textContent = `${PERFORMANCE.fps} FPS · ${PERFORMANCE.quality}`;
      }
    }
  }

  function setQualityLevel(tier) {
    PERFORMANCE.quality = tier;
    switch (tier) {
      case 'Minimal':
        PERFORMANCE.qualityScale = 0.2;
        CONFIG.ENABLE_SMOKE = false;
        CONFIG.ENABLE_SHAKE = false;
        break;
      case 'Low':
        PERFORMANCE.qualityScale = 0.45;
        CONFIG.ENABLE_SMOKE = !isReducedMotion;
        CONFIG.ENABLE_SHAKE = false;
        break;
      case 'Medium':
        PERFORMANCE.qualityScale = 0.75;
        CONFIG.ENABLE_SMOKE = !isReducedMotion;
        CONFIG.ENABLE_SHAKE = !isReducedMotion;
        break;
      case 'High':
      default:
        PERFORMANCE.qualityScale = 1.0;
        CONFIG.ENABLE_SMOKE = !isReducedMotion;
        CONFIG.ENABLE_SHAKE = !isReducedMotion;
        break;
    }
  }

  // --------------------------------------------------------------------------
  // 5. STARFIELD BACKGROUND SYSTEM
  // --------------------------------------------------------------------------
  function initStarfield() {
    stars = [];
    const count = isReducedMotion ? Math.floor(CONFIG.STAR_COUNT * 0.3) : CONFIG.STAR_COUNT;
    for (let i = 0; i < count; i++) {
      stars.push({
        x: Math.random() * viewportWidth,
        y: Math.random() * viewportHeight,
        radius: Math.random() * 1.5 + 0.3,
        baseAlpha: Math.random() * 0.5 + 0.2,
        twinkleSpeed: Math.random() * 2.2 + 0.8,
        twinklePhase: Math.random() * Math.PI * 2,
        depth: Math.random() * 0.035 + 0.008,
        color: Math.random() > 0.82 ? '#00E5FF' : (Math.random() > 0.88 ? '#D500F9' : '#FFFFFF')
      });
    }
  }

  function renderStarfield(timeInSec, mouseX, mouseY) {
    if (!CONFIG.ENABLE_STARS || PERFORMANCE.quality === 'Minimal') return;

    const centerX = viewportWidth * 0.5;
    const centerY = viewportHeight * 0.5;
    const offsetX = (mouseX - centerX);
    const offsetY = (mouseY - centerY);

    ctx.save();
    for (let i = 0; i < stars.length; i++) {
      const star = stars[i];
      const alpha = star.baseAlpha + Math.sin(timeInSec * star.twinkleSpeed + star.twinklePhase) * 0.22;
      const currentAlpha = Math.max(0.06, Math.min(1.0, alpha));

      const px = star.x - offsetX * star.depth;
      const py = star.y - offsetY * star.depth;

      ctx.fillStyle = star.color;
      ctx.globalAlpha = currentAlpha;
      ctx.beginPath();
      ctx.arc(px, py, star.radius, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  // --------------------------------------------------------------------------
  // 6. PARTICLE CREATION & EXPLOSION HANDLERS (POOLED)
  // --------------------------------------------------------------------------
  function triggerScreenShake(magnitude) {
    if (!CONFIG.ENABLE_SHAKE || isReducedMotion || PERFORMANCE.quality === 'Minimal' || PERFORMANCE.quality === 'Low') return;
    shakeIntensity = Math.max(shakeIntensity, magnitude);
  }

  function spawnSmoke(x, y, vx, vy, thrust) {
    if (!CONFIG.ENABLE_SMOKE || isReducedMotion) return;

    const p = pool.obtain('smoke');
    if (!p) return; // Pool full (strictly respects MAX_PARTICLES)

    const angleSpread = (Math.random() - 0.5) * 0.65;
    const speed = (CONFIG.SMOKE_SPEED_MIN + Math.random() * (CONFIG.SMOKE_SPEED_MAX - CONFIG.SMOKE_SPEED_MIN)) * (1 + thrust * 0.7);

    p.x = x;
    p.y = y;
    p.vx = vx * 0.12 + Math.sin(rocket.angle + Math.PI + angleSpread) * speed;
    p.vy = vy * 0.12 - Math.cos(rocket.angle + Math.PI + angleSpread) * speed;
    p.radius = Math.random() * 3.5 + 2.5;
    p.maxRadius = Math.random() * 10 + CONFIG.SMOKE_EXPANSION * (1 + thrust * 0.4);
    p.life = 0;
    p.maxLife = CONFIG.SMOKE_LIFETIME * (Math.random() * 0.4 + 0.8);
    p.rotation = Math.random() * Math.PI * 2;
    p.rotSpeed = (Math.random() - 0.5) * 1.5;
    p.baseAlpha = Math.random() * 0.2 + 0.42;
  }

  function spawnFirework(x, y, multiplier = 1.0, specificPalette = null) {
    const palette = specificPalette || PALETTES[Math.floor(Math.random() * PALETTES.length)];
    const scale = multiplier * PERFORMANCE.qualityScale;
    const baseCount = isReducedMotion ? 12 : CONFIG.FIREWORK_PARTICLES;
    const count = Math.floor(baseCount * scale);

    // 1. Central flash flare
    const flare = pool.obtain('flare');
    if (flare) {
      flare.x = x;
      flare.y = y;
      flare.radius = 38 * scale;
      flare.maxLife = 0.18;
      flare.color = palette.colors[0];
    }

    // 2. Expanding shockwave ring
    if (!isReducedMotion && PERFORMANCE.quality !== 'Minimal') {
      const ring = pool.obtain('shockwave');
      if (ring) {
        ring.x = x;
        ring.y = y;
        ring.radius = 4;
        ring.maxRadius = 70 * scale;
        ring.maxLife = 0.42;
        ring.color = palette.colors[1];
      }
    }

    // 3. Radial Sparks
    for (let i = 0; i < count; i++) {
      const spark = pool.obtain('spark');
      if (!spark) break; // Global MAX_PARTICLES ceiling reached

      const angle = Math.random() * Math.PI * 2;
      const speed = (Math.random() * 250 + 40) * Math.sqrt(Math.random()) * scale;
      const color = palette.colors[Math.floor(Math.random() * palette.colors.length)];

      spark.x = x;
      spark.y = y;
      spark.prevX = x;
      spark.prevY = y;
      spark.vx = Math.cos(angle) * speed;
      spark.vy = Math.sin(angle) * speed;
      spark.size = Math.random() * 2.6 + 1.2;
      spark.color = color;
      spark.alpha = 1.0;
      spark.maxLife = CONFIG.PARTICLE_DECAY * (Math.random() * 0.5 + 0.75);
      spark.isTwinkle = Math.random() > 0.65;
      spark.twinkleSpeed = Math.random() * 24 + 10;
      spark.isSecondaryBurst = !isReducedMotion && Math.random() > 0.84 && PERFORMANCE.quality === 'High';
      spark.hasBurst = false;
    }

    triggerScreenShake(7 * scale);
  }

  // --------------------------------------------------------------------------
  // 7. ROCKET PROCEDURAL RENDERING
  // --------------------------------------------------------------------------
  function drawRocket(ctx, r, timeInSec) {
    ctx.save();
    ctx.translate(r.x, r.y);
    ctx.rotate(r.angle);

    // Roll banking scale
    const rollScaleX = Math.max(0.68, 1 - Math.abs(r.banking) * CONFIG.BANKING_FACTOR);
    ctx.scale(rollScaleX, 1);

    const length = 46;
    const width = 22;
    const halfW = width * 0.5;

    // --- A. ENGINE FLAME & NOZZLE GLOW (SCALED BY ENGINE_GLOW) ---
    const thrust = r.engineThrust;
    const flameLength = (16 + thrust * 28) * (0.88 + Math.sin(timeInSec * 45) * 0.12);
    const flameWidth = halfW * 0.75;
    const nozzleY = length * 0.48;
    const glowScale = CONFIG.ENGINE_GLOW;

    ctx.save();
    ctx.globalCompositeOperation = 'lighter';

    // Outer Glow Plume
    const glowRadius = flameLength * 1.4 * glowScale;
    const glowGrad = ctx.createRadialGradient(0, nozzleY + 6, 2, 0, nozzleY + 8, Math.max(4, glowRadius));
    glowGrad.addColorStop(0, `rgba(0, 229, 255, ${0.9 * glowScale})`);
    glowGrad.addColorStop(0.35, `rgba(121, 0, 255, ${0.6 * glowScale})`);
    glowGrad.addColorStop(0.75, `rgba(255, 45, 170, ${0.25 * glowScale})`);
    glowGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
    ctx.fillStyle = glowGrad;
    ctx.beginPath();
    ctx.arc(0, nozzleY + 8, Math.max(4, glowRadius), 0, Math.PI * 2);
    ctx.fill();

    // Core Plasma Tongue
    const flameGrad = ctx.createLinearGradient(0, nozzleY, 0, nozzleY + flameLength);
    flameGrad.addColorStop(0, '#FFFFFF');
    flameGrad.addColorStop(0.2, '#00E5FF');
    flameGrad.addColorStop(0.6, '#087BFF');
    flameGrad.addColorStop(0.9, '#D500F9');
    flameGrad.addColorStop(1, 'rgba(121, 0, 255, 0)');

    ctx.fillStyle = flameGrad;
    ctx.beginPath();
    ctx.moveTo(-flameWidth * 0.5, nozzleY);
    ctx.quadraticCurveTo(0, nozzleY + flameLength * 1.15, 0, nozzleY + flameLength);
    ctx.quadraticCurveTo(0, nozzleY + flameLength * 1.15, flameWidth * 0.5, nozzleY);
    ctx.closePath();
    ctx.fill();

    // Inner White Core
    ctx.fillStyle = 'rgba(255, 255, 255, 0.95)';
    ctx.beginPath();
    ctx.moveTo(-flameWidth * 0.22, nozzleY);
    ctx.lineTo(0, nozzleY + flameLength * 0.45);
    ctx.lineTo(flameWidth * 0.22, nozzleY);
    ctx.closePath();
    ctx.fill();

    ctx.restore();

    // --- B. METALLIC ENGINE BELL ---
    ctx.fillStyle = '#1E293B';
    ctx.strokeStyle = '#475569';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.moveTo(-halfW * 0.38, nozzleY - 4);
    ctx.lineTo(-halfW * 0.48, nozzleY + 2);
    ctx.lineTo(halfW * 0.48, nozzleY + 2);
    ctx.lineTo(halfW * 0.38, nozzleY - 4);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // --- C. WINGS / DELTA FINS ---
    // Left Wing
    const wingGradL = ctx.createLinearGradient(-width * 1.4, 0, 0, 0);
    wingGradL.addColorStop(0, '#00E5FF');
    wingGradL.addColorStop(0.5, '#101B63');
    wingGradL.addColorStop(1, '#0C1246');
    ctx.fillStyle = wingGradL;
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.6)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(-halfW * 0.7, 0);
    ctx.lineTo(-width * 1.35, nozzleY + 1);
    ctx.lineTo(-halfW * 0.6, nozzleY - 2);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Left Tip Light
    ctx.fillStyle = '#00E5FF';
    ctx.beginPath();
    ctx.arc(-width * 1.32, nozzleY, 2, 0, Math.PI * 2);
    ctx.fill();

    // Right Wing
    const wingGradR = ctx.createLinearGradient(0, 0, width * 1.4, 0);
    wingGradR.addColorStop(0, '#0C1246');
    wingGradR.addColorStop(0.5, '#7900FF');
    wingGradR.addColorStop(1, '#D500F9');
    ctx.fillStyle = wingGradR;
    ctx.strokeStyle = 'rgba(213, 0, 249, 0.6)';
    ctx.beginPath();
    ctx.moveTo(halfW * 0.7, 0);
    ctx.lineTo(width * 1.35, nozzleY + 1);
    ctx.lineTo(halfW * 0.6, nozzleY - 2);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Right Tip Light
    ctx.fillStyle = '#FF2DAA';
    ctx.beginPath();
    ctx.arc(width * 1.32, nozzleY, 2, 0, Math.PI * 2);
    ctx.fill();

    // --- D. MAIN FUSELAGE ---
    const hullGrad = ctx.createLinearGradient(-halfW, 0, halfW, 0);
    hullGrad.addColorStop(0, '#CBD5E1');
    hullGrad.addColorStop(0.25, '#FFFFFF');
    hullGrad.addColorStop(0.7, '#E2E8F0');
    hullGrad.addColorStop(1, '#94A3B8');
    ctx.fillStyle = hullGrad;
    ctx.strokeStyle = '#FFFFFF';
    ctx.lineWidth = 1.2;

    ctx.beginPath();
    ctx.moveTo(0, -length * 0.52);
    ctx.bezierCurveTo(halfW * 1.15, -length * 0.2, halfW * 0.95, length * 0.35, halfW * 0.45, nozzleY);
    ctx.lineTo(-halfW * 0.45, nozzleY);
    ctx.bezierCurveTo(-halfW * 0.95, length * 0.35, -halfW * 1.15, -length * 0.2, 0, -length * 0.52);
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Center longitudinal highlight
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.75)';
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(-1, -length * 0.42);
    ctx.lineTo(-1, length * 0.25);
    ctx.stroke();

    // Nose Cone Accent
    ctx.fillStyle = '#00E5FF';
    ctx.beginPath();
    ctx.moveTo(0, -length * 0.52);
    ctx.lineTo(halfW * 0.38, -length * 0.35);
    ctx.lineTo(-halfW * 0.38, -length * 0.35);
    ctx.closePath();
    ctx.fill();

    // --- E. GLASS COCKPIT CANOPY ---
    const canopyGrad = ctx.createLinearGradient(0, -length * 0.32, 0, 0);
    canopyGrad.addColorStop(0, '#00E5FF');
    canopyGrad.addColorStop(0.4, '#087BFF');
    canopyGrad.addColorStop(1, '#080816');
    ctx.fillStyle = canopyGrad;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.85)';
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.ellipse(0, -length * 0.12, halfW * 0.38, length * 0.16, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();

    // Reflection Glare
    ctx.fillStyle = 'rgba(255, 255, 255, 0.75)';
    ctx.beginPath();
    ctx.ellipse(-1.5, -length * 0.16, halfW * 0.15, length * 0.06, -0.2, 0, Math.PI * 2);
    ctx.fill();

    // Center Dorsal Fin
    ctx.fillStyle = '#64748B';
    ctx.beginPath();
    ctx.moveTo(0, -length * 0.05);
    ctx.lineTo(1.2, length * 0.3);
    ctx.lineTo(-1.2, length * 0.3);
    ctx.closePath();
    ctx.fill();

    ctx.restore();
  }

  // --------------------------------------------------------------------------
  // 8. MAIN ANIMATION & PHYSICS ENGINE LOOP
  // --------------------------------------------------------------------------
  function engineLoop(currentTimestamp) {
    // Delta-time clamped to handle background tab pauses smoothly
    const dtRaw = (currentTimestamp - lastTimestamp) / 1000;
    const dt = Math.max(0.001, Math.min(dtRaw, 0.08));
    lastTimestamp = currentTimestamp;
    const timeInSec = currentTimestamp * 0.001;

    // Update adaptive performance monitor
    updatePerformance(dt, currentTimestamp);

    // --- 1. ROCKET INERTIAL PHYSICS WITH ROCKET_SPEED DISPLACEMENT CLAMP ---
    const dx = rocket.targetX - rocket.x;
    const dy = rocket.targetY - rocket.y;
    const dist = Math.hypot(dx, dy);

    // Frame-rate normalized positional interpolation
    const smoothingFactor = Math.min(1.0, CONFIG.ROCKET_SMOOTHING * (dt * 60));
    let stepX = dx * smoothingFactor;
    let stepY = dy * smoothingFactor;
    let stepDist = Math.hypot(stepX, stepY);

    // Enforce ROCKET_SPEED as an authentic maximum step clamp
    const maxAllowedStep = CONFIG.ROCKET_SPEED * (dt * 60);
    if (stepDist > maxAllowedStep && stepDist > 0.0001) {
      const clampRatio = maxAllowedStep / stepDist;
      stepX *= clampRatio;
      stepY *= clampRatio;
      stepDist = maxAllowedStep;
    }

    rocket.vx = stepX / dt;
    rocket.vy = stepY / dt;
    rocket.speed = stepDist / dt;

    rocket.x += stepX;
    rocket.y += stepY;

    // Rocket thrust response
    const targetThrust = Math.min(1.0, rocket.speed / 450);
    rocket.engineThrust += (targetThrust - rocket.engineThrust) * Math.min(1.0, 10 * dt);

    // --- 2. ROCKET ROTATION WITH SHORTEST-ARC ANGULAR INTERPOLATION ---
    const now = performance.now();
    if (dist > 2.0) {
      rocket.lastMoveTime = now;
      // 0 rad = facing upright (-Y direction)
      rocket.targetAngle = Math.atan2(dy, dx) + Math.PI * 0.5;
    } else if (now - rocket.lastMoveTime > CONFIG.RESTING_TIMEOUT) {
      rocket.targetAngle = CONFIG.RESTING_ANGLE;
    }

    // Shortest-arc angle difference: prevents sudden ±180° rotation flips
    let angleDiff = ((rocket.targetAngle - rocket.angle + Math.PI) % (Math.PI * 2)) - Math.PI;
    if (angleDiff < -Math.PI) angleDiff += Math.PI * 2;

    const rotSmooth = Math.min(1.0, CONFIG.ROTATION_SMOOTHING * (dt * 60));
    rocket.angularVelocity = angleDiff * rotSmooth;
    rocket.angle += rocket.angularVelocity;

    // Dynamic banking compression
    rocket.banking += (rocket.angularVelocity * 10 - rocket.banking) * Math.min(1.0, 8 * dt);

    // --- 3. SMOKE TRAIL EMISSION FROM NOZZLE ---
    if (CONFIG.ENABLE_SMOKE && rocket.isActive && rocket.isFinePointer) {
      accumulatedSmoke += CONFIG.SMOKE_RATE * (1 + rocket.engineThrust * 1.5) * (dt * 60) * PERFORMANCE.qualityScale;
      while (accumulatedSmoke >= 1.0) {
        accumulatedSmoke -= 1.0;
        const nozzleOffset = 22;
        const nozzleWorldX = rocket.x + Math.sin(rocket.angle) * nozzleOffset;
        const nozzleWorldY = rocket.y - Math.cos(rocket.angle) * nozzleOffset;
        spawnSmoke(nozzleWorldX, nozzleWorldY, rocket.vx, rocket.vy, rocket.engineThrust);
      }
    }

    // --- 4. CLEAR CANVAS & DRAW BACKGROUND ---
    ctx.clearRect(0, 0, viewportWidth, viewportHeight);
    renderStarfield(timeInSec, rocket.x, rocket.y);

    // --- 5. POOLED PARTICLES UPDATE & RENDER ---
    const active = pool.activeList;
    for (let i = active.length - 1; i >= 0; i--) {
      const p = active[i];
      p.life += dt;
      if (p.life >= p.maxLife) {
        // Optional secondary burst before deallocation
        if (p.type === 'spark' && p.isSecondaryBurst && !p.hasBurst) {
          p.hasBurst = true;
          for (let k = 0; k < 5; k++) {
            const micro = pool.obtain('spark');
            if (!micro) break; // Global ceiling enforced
            const microAngle = Math.random() * Math.PI * 2;
            const microSpeed = Math.random() * 45 + 15;
            micro.x = p.x;
            micro.y = p.y;
            micro.prevX = p.x;
            micro.prevY = p.y;
            micro.vx = Math.cos(microAngle) * microSpeed;
            micro.vy = Math.sin(microAngle) * microSpeed;
            micro.size = p.size * 0.65;
            micro.color = p.color;
            micro.alpha = 1.0;
            micro.maxLife = 0.32;
            micro.isTwinkle = true;
            micro.twinkleSpeed = 30;
            micro.isSecondaryBurst = false;
            micro.hasBurst = true;
          }
        }
        pool.releaseAt(i);
        continue;
      }

      // Update particle physics by type
      if (p.type === 'smoke') {
        p.x += p.vx * dt;
        p.y += p.vy * dt;
        p.vx *= Math.pow(0.98, dt * 60);
        p.vy *= Math.pow(0.98, dt * 60);
        p.rotation += p.rotSpeed * dt;

        const progress = p.life / p.maxLife;
        const currentRadius = p.radius + (p.maxRadius - p.radius) * Math.sin(progress * Math.PI * 0.5);
        const currentAlpha = p.baseAlpha * Math.pow(1 - progress, 1.4);

        const grad = ctx.createRadialGradient(p.x, p.y, currentRadius * 0.1, p.x, p.y, Math.max(1, currentRadius));
        grad.addColorStop(0, `rgba(240, 248, 255, ${currentAlpha * 0.85})`);
        grad.addColorStop(0.4, `rgba(180, 210, 255, ${currentAlpha * 0.45})`);
        grad.addColorStop(0.8, `rgba(121, 0, 255, ${currentAlpha * 0.15})`);
        grad.addColorStop(1, 'rgba(12, 18, 70, 0)');

        ctx.fillStyle = grad;
        ctx.beginPath();
        ctx.arc(p.x, p.y, Math.max(1, currentRadius), 0, Math.PI * 2);
        ctx.fill();

      } else if (p.type === 'flare') {
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        const progress = p.life / p.maxLife;
        const alpha = (1 - progress) * 0.8;
        const grad = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, Math.max(1, p.radius));
        grad.addColorStop(0, '#FFFFFF');
        grad.addColorStop(0.35, p.color);
        grad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = grad;
        ctx.globalAlpha = alpha;
        ctx.beginPath();
        ctx.arc(p.x, p.y, Math.max(1, p.radius), 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();

      } else if (p.type === 'shockwave') {
        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        const progress = p.life / p.maxLife;
        const currentRadius = p.radius + (p.maxRadius - p.radius) * Math.pow(progress, 0.4);
        const alpha = (1 - progress) * 0.6;
        ctx.strokeStyle = p.color;
        ctx.lineWidth = Math.max(0.5, 3 * (1 - progress));
        ctx.globalAlpha = alpha;
        ctx.beginPath();
        ctx.arc(p.x, p.y, Math.max(1, currentRadius), 0, Math.PI * 2);
        ctx.stroke();
        ctx.restore();

      } else if (p.type === 'spark') {
        p.prevX = p.x;
        p.prevY = p.y;
        p.vx *= Math.pow(CONFIG.PARTICLE_FRICTION, dt * 60);
        p.vy = p.vy * Math.pow(CONFIG.PARTICLE_FRICTION, dt * 60) + CONFIG.FIREWORK_GRAVITY * dt;
        p.x += p.vx * dt;
        p.y += p.vy * dt;

        const progress = p.life / p.maxLife;
        let alpha = 1 - progress;
        if (p.isTwinkle) {
          alpha *= (0.4 + 0.6 * Math.sin(timeInSec * p.twinkleSpeed));
        }
        p.alpha = Math.max(0, Math.min(1.0, alpha));

        ctx.save();
        ctx.globalCompositeOperation = 'lighter';
        ctx.strokeStyle = p.color;
        ctx.lineWidth = p.size;
        ctx.globalAlpha = p.alpha;
        ctx.beginPath();
        ctx.moveTo(p.prevX, p.prevY);
        ctx.lineTo(p.x, p.y);
        ctx.stroke();

        ctx.fillStyle = '#FFFFFF';
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * 0.6, 0, Math.PI * 2);
        ctx.fill();
        ctx.restore();
      }
    }

    // --- 6. DRAW ROCKET CURSOR ---
    if (CONFIG.ENABLE_CUSTOM_CURSOR && rocket.isActive && rocket.isFinePointer) {
      drawRocket(ctx, rocket, timeInSec);
    }

    // --- 7. TIME-NORMALIZED SCREEN SHAKE DECAY ---
    if (shakeContainer) {
      if (shakeIntensity > 0.05) {
        const shakeX = (Math.random() - 0.5) * shakeIntensity * 1.4;
        const shakeY = (Math.random() - 0.5) * shakeIntensity * 1.4;
        shakeContainer.style.transform = `translate3d(${shakeX.toFixed(2)}px, ${shakeY.toFixed(2)}px, 0)`;
        // Decay normalized by delta time
        shakeIntensity *= Math.pow(CONFIG.SHAKE_DECAY, dt * 60);
      } else if (shakeIntensity !== 0) {
        shakeIntensity = 0;
        shakeContainer.style.transform = 'translate3d(0, 0, 0)';
      }
    }

    // Request next frame
    animFrameId = requestAnimationFrame(engineLoop);
  }

  // --------------------------------------------------------------------------
  // 9. POINTER EVENTS & STRICT EVENT ISOLATION
  // --------------------------------------------------------------------------
  function isInteractiveControl(target) {
    if (!target) return false;
    // Check if clicked inside a button, link, form control, or flagged container
    return Boolean(target.closest('button, a, input, textarea, select, .controls-dock, .interactive-panel, [data-no-fx]'));
  }

  function handlePointerMove(e) {
    rocket.isFinePointer = (e.pointerType !== 'touch');
    rocket.targetX = e.clientX;
    rocket.targetY = e.clientY;
    if (!rocket.isActive) {
      rocket.x = e.clientX;
      rocket.y = e.clientY;
      rocket.isActive = true;
    }
  }

  function handlePointerDown(e) {
    rocket.isPointerDown = true;
    rocket.pointerDownTime = performance.now();

    // Event isolation: if user clicked an interactive control, do NOT trigger background firework!
    if (isInteractiveControl(e.target)) {
      return;
    }

    spawnFirework(e.clientX, e.clientY, 1.0);
  }

  function handlePointerUp(e) {
    if (rocket.isPointerDown) {
      const holdDuration = (performance.now() - rocket.pointerDownTime) / 1000;
      // Supernova hold-to-charge mechanic
      if (holdDuration > 0.35 && !isInteractiveControl(e.target)) {
        const power = Math.min(2.4, 1.0 + holdDuration * 1.2);
        spawnFirework(e.clientX, e.clientY, power);
      }
    }
    rocket.isPointerDown = false;
  }

  function handlePointerLeave() {
    rocket.targetAngle = CONFIG.RESTING_ANGLE;
    rocket.targetX = rocket.x;
    rocket.targetY = rocket.y;
    rocket.engineThrust = 0;
  }

  // --------------------------------------------------------------------------
  // 10. INITIALIZATION & PUBLIC API
  // --------------------------------------------------------------------------
  function resize() {
    if (!canvas) return;
    viewportWidth = window.innerWidth;
    viewportHeight = window.innerHeight;
    dpr = Math.min(window.devicePixelRatio || 1, 2);

    canvas.width = viewportWidth * dpr;
    canvas.height = viewportHeight * dpr;
    canvas.style.width = `${viewportWidth}px`;
    canvas.style.height = `${viewportHeight}px`;

    ctx.resetTransform();
    ctx.scale(dpr, dpr);

    initStarfield();
  }

  function init(options = {}) {
    canvas = document.getElementById(options.canvasId || 'fx-canvas');
    if (!canvas) {
      console.warn('[CosmicEngine] Canvas element not found. Animation disabled.');
      return;
    }
    ctx = canvas.getContext('2d', { alpha: true });
    shakeContainer = document.getElementById(options.shakeId || 'shake-wrapper');

    // Create pooled particle store
    pool = new ParticlePool(CONFIG.MAX_PARTICLES);

    // Detect media query prefers-reduced-motion
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    isReducedMotion = motionQuery.matches;
    motionQuery.addEventListener('change', (e) => {
      isReducedMotion = e.matches;
      if (isReducedMotion) {
        CONFIG.ENABLE_SMOKE = false;
        CONFIG.ENABLE_SHAKE = false;
        CONFIG.FIREWORK_PARTICLES = 15;
      } else {
        CONFIG.ENABLE_SMOKE = true;
        CONFIG.ENABLE_SHAKE = true;
        CONFIG.FIREWORK_PARTICLES = 75;
      }
      initStarfield();
    });

    // Detect fine pointer vs touch device
    const pointerFineQuery = window.matchMedia('(pointer: fine)');
    rocket.isFinePointer = pointerFineQuery.matches;

    if (rocket.isFinePointer && CONFIG.ENABLE_CUSTOM_CURSOR) {
      document.body.classList.add('custom-cursor-active');
    }

    // Bind Pointer Events (Supports Mouse, Pen, Touch with Pointer Events API)
    window.addEventListener('pointermove', handlePointerMove, { passive: true });
    window.addEventListener('pointerdown', handlePointerDown, { passive: true });
    window.addEventListener('pointerup', handlePointerUp, { passive: true });
    document.addEventListener('mouseleave', handlePointerLeave, { passive: true });
    window.addEventListener('resize', resize, { passive: true });

    resize();
    lastTimestamp = performance.now();
    animFrameId = requestAnimationFrame(engineLoop);

    return {
      config: CONFIG,
      performance: PERFORMANCE,
      spawnFirework,
      setQualityLevel
    };
  }

  return {
    init,
    CONFIG,
    PERFORMANCE,
    spawnFirework
  };
}));
