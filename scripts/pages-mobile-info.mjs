const MOBILE_INFO_STYLE = `<style>
.info{touch-action:manipulation;user-select:none}.info:focus{outline:2px solid #7fb6de;outline-offset:2px}.infoPopover{position:fixed;left:50%;bottom:18px;transform:translateX(-50%);width:min(92vw,520px);display:none;background:#08141e;border:1px solid #41647e;border-radius:12px;padding:12px 38px 12px 14px;color:#e7eff5;font-size:13px;line-height:1.5;box-shadow:0 12px 38px rgba(0,0,0,.45);z-index:1000}.infoPopover.show{display:block}.infoPopoverClose{position:absolute;right:8px;top:7px;border:0;background:transparent;color:#a9bdcc;font-size:20px;line-height:1;cursor:pointer;padding:4px 8px}
</style>`;

const MOBILE_INFO_SCRIPT = `<script>
(function(){
  const pop=document.getElementById('infoPopover');
  const text=document.getElementById('infoPopoverText');
  const close=document.getElementById('infoPopoverClose');
  if(!pop||!text)return;
  let timer=null;
  function hide(){pop.classList.remove('show');if(timer)clearTimeout(timer)}
  function show(el){const msg=el.getAttribute('title');if(!msg)return;text.textContent=msg;pop.classList.add('show');if(timer)clearTimeout(timer);timer=setTimeout(hide,8000)}
  document.querySelectorAll('.info').forEach(el=>{
    el.setAttribute('tabindex','0');el.setAttribute('role','button');el.setAttribute('aria-label','Više informacija');
    el.addEventListener('click',e=>{e.preventDefault();e.stopPropagation();show(el)});
    el.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();show(el)}});
  });
  close?.addEventListener('click',hide);
  document.addEventListener('keydown',e=>{if(e.key==='Escape')hide()});
  document.addEventListener('click',e=>{if(pop.classList.contains('show')&&!pop.contains(e.target)&&!e.target.closest?.('.info'))hide()});
})();
</script>`;

export function enhanceMobileInfo(input) {
  if (!input.includes('class="info"')) throw new Error('Pages info markers missing');
  let html = input.replace('</head>', `${MOBILE_INFO_STYLE}\n</head>`);
  html = html.replace('</main>', '<div id="infoPopover" class="infoPopover" role="status" aria-live="polite"><button id="infoPopoverClose" class="infoPopoverClose" aria-label="Zatvori">×</button><div id="infoPopoverText"></div></div></main>');
  html = html.replace('</body>', `${MOBILE_INFO_SCRIPT}\n</body>`);
  return html;
}
