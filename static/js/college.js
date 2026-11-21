document.addEventListener("DOMContentLoaded",()=>{
  const counters=document.querySelectorAll("[data-count]");
  counters.forEach(el=>{const target=Number(el.dataset.count||0);if(!target)return;let start=0;const duration=850;const began=performance.now();function tick(now){const p=Math.min((now-began)/duration,1);start=Math.floor(target*(1-Math.pow(1-p,3)));el.textContent=start.toLocaleString("en-IN");if(p<1)requestAnimationFrame(tick)}requestAnimationFrame(tick)});
  const rows=document.querySelectorAll(".bar-row");rows.forEach((row,i)=>{const number=Number(row.querySelector("b")?.textContent||0);const max=Math.max(...[...rows].map(r=>Number(r.querySelector("b")?.textContent||0)),1);row.querySelector(".bar-track i")?.style.setProperty("--target",`${Math.max(5,number/max*100)}%`)});
});
