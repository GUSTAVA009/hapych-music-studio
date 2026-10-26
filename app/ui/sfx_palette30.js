"use strict";
document.addEventListener("DOMContentLoaded",()=>{
 const $=id=>document.getElementById(id);
 const words=$("songWords"),style=$("songStyle");
 if(!words||!style)return;
 const css=document.createElement("style");
 css.textContent=[
 "#studioSfxCatalog{width:min(940px,96vw);height:min(770px,85vh);max-height:85vh;background:#15171d;color:#f3f3f4;border:1px solid #434751;border-radius:16px;padding:22px;overflow:hidden}",
 "#studioSfxCatalog::backdrop{background:rgba(0,0,0,.72)}",
 ".sfx30-top,.sfx30-row,.sfx30-controls{display:flex;gap:10px;align-items:center;justify-content:space-between}",
 ".sfx30-top h2{font-size:23px;margin:0}",
 ".sfx30-search{width:100%;padding:12px;background:#20242c;color:#fff;border:1px solid #444a56;border-radius:9px;margin:15px 0}",
 ".sfx30-list{height:calc(100% - 138px);overflow:auto;display:flex;flex-direction:column;gap:7px}",
 ".sfx30-row{padding:11px;border-radius:9px;background:#22252c;border:1px solid #2d333d}",
 ".sfx30-name{min-width:0;overflow-wrap:anywhere;flex:1}",
 ".sfx30-name strong{display:block;font-size:14px}.sfx30-name small{opacity:.66}",
 ".sfx30-controls button,.sfx30-top button{padding:8px 12px;border:1px solid #555a67;background:#303540;color:#fff;border-radius:8px;cursor:pointer}",
 ".sfx30-controls button:last-child{background:#6654bb;border-color:#6654bb}",
 ".sfx30-status{color:#aeb1b9;margin:7px 0;font-size:12px}",
 "#studioStyleCheck{display:block;text-align:left;margin:8px 0;padding:13px;border:1px solid #363a43;border-radius:10px;background:#1b1d23;color:#ddd;white-space:pre-wrap;max-height:280px;overflow:auto}",
 "#studioStyleCheck[hidden]{display:none}"
 ].join("\n");
 document.head.appendChild(css);
 const dialog=document.createElement("dialog");dialog.id="studioSfxCatalog";
 dialog.setAttribute("aria-label","Каталог звуковых эффектов Music Studio");
 dialog.innerHTML='<div class="sfx30-top"><h2>Каталог SFX</h2><button type="button" id="sfx30Close">Закрыть ×</button></div>'+
 '<p class="sfx30-status" id="sfx30Status">Загружаем звуки…</p>'+
 '<input class="sfx30-search" id="sfx30Search" type="search" placeholder="Thunder, шаги, car, phone, coin…" aria-label="Поиск SFX">'+
 '<div class="sfx30-list" id="sfx30List"></div>';
 document.body.appendChild(dialog);
 $("sfx30Close").addEventListener("click",()=>dialog.close());
 let audio=null;
 dialog.addEventListener("close",()=>{if(audio){audio.pause();audio=null;}});
 const open=document.createElement("button");open.type="button";open.className="small-action";open.textContent="Каталог SFX";
 open.title="Поиск, прослушивание и вставка звуковых эффектов";
 const write=$("writeLyrics");
 if(write)write.parentElement.insertBefore(open,write);
 let data=null,items=[];
 function add(x){
  const row=document.createElement("div");row.className="sfx30-row";
  const name=document.createElement("div");name.className="sfx30-name";
  const title=document.createElement("strong");title.textContent=x.label;
  const desc=document.createElement("small");desc.textContent=x.group;
  name.append(title,desc);
  const controls=document.createElement("div");controls.className="sfx30-controls";
  const preview=document.createElement("button");preview.type="button";preview.textContent="▶";preview.title="Прослушать";
  preview.addEventListener("click",()=>{
   if(audio)audio.pause();
   audio=new Audio("/api/sfx/sample?key="+encodeURIComponent(x.key));
   audio.play().catch(()=>$("sfx30Status").textContent="Не удалось прослушать запись");
  });
  const select=document.createElement("button");select.type="button";select.textContent="+ В текст";
  select.addEventListener("click",()=>{
   const pos=words.selectionStart??words.value.length;
   words.setRangeText("\n[SFX: "+x.key+"]\n",pos,words.selectionEnd??pos,"end");
   words.dispatchEvent(new Event("input",{bubbles:true}));
   dialog.close();words.focus();
  });
  controls.append(preview,select);row.append(name,controls);$("sfx30List").appendChild(row);
 }
 function render(){
  const q=$("sfx30Search").value.toLowerCase().trim();
  $("sfx30List").replaceChildren();
  const hits=q?items.filter(x=>x.search.includes(q)):items.filter(x=>x.type!=="sample");
  hits.slice(0,70).forEach(add);
  $("sfx30Status").textContent="Файлов: "+(data?.total_imported_audio||0)+
    "; категорий: "+(data?.mapped_categories||0)+
    "; найдено: "+hits.length+" (показано до 70).";
 }
 $("sfx30Search").addEventListener("input",render);
 open.addEventListener("click",async()=>{
  dialog.showModal();
  if(!data){
   try{
    const response=await fetch("/api/sfx/catalog",{cache:"no-store"});
    if(!response.ok)throw Error("HTTP "+response.status);
    data=await response.json();
    items=[
     ...(data.categories||[]).map(x=>({type:"category",key:x.id,label:x.id.replaceAll("_"," "),group:x.group+" · "+x.count+" вариантов"})),
     ...(data.built_in_effects||[]).map(x=>({type:"built_in",key:x,label:x.replaceAll("_"," "),group:"Встроенный SFX"})),
     ...(data.samples||[]).map(x=>({type:"sample",key:x.key,label:x.label,group:x.group+" · запись"}))
    ];
    // Real field recordings before synthesized/retro sounds in discovery.
    items.sort((a,b)=>Number(b.group.includes("owlish_recorded"))-Number(a.group.includes("owlish_recorded")));
    items.forEach(x=>x.search=(x.label+" "+x.group+" "+x.key).toLowerCase());
   }catch(err){$("sfx30Status").textContent="Ошибка загрузки: "+err.message;return;}
  }
  render();$("sfx30Search").focus();
 });
 const check=document.createElement("button");
 check.type="button";check.className="small-action";check.textContent="Проверить промпт";
 check.title="Сравнить полный текст с тем, что реально получает ACE-Step";
 const area=style.closest(".writing-area");
 if(area){
  area.parentNode.insertBefore(check,area.nextSibling);
  const info=document.createElement("div");info.id="studioStyleCheck";info.hidden=true;
  check.insertAdjacentElement("afterend",info);
  style.addEventListener("input",()=>info.hidden=true);
  words.addEventListener("input",()=>info.hidden=true);
  check.addEventListener("click",async()=>{
   info.hidden=false;info.textContent="Анализируем музыкальное описание…";
   try{
    const body={style:style.value,lyrics:words.value,vocal_language:"auto",vocal_gender:"auto",instrumental:false};
    const response=await fetch("/api/prepare",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    const p=await response.json();
    if(!response.ok)throw Error(p.error||"HTTP "+response.status);
    const missing=p.style_plan?.not_sent_to_model||[];
    const styleFx=p.style_sfx_added||[];
    info.textContent="Исходное описание: "+style.value.length+" символов\n"+
     "В ACE-Step: "+p.caption.length+"/512 символов\n"+
     "SFX-событий в плане: "+(p.effects_plan?.length||0)+"\n\n"+
     "Текст, который получает модель:\n"+p.caption+"\n\n"+
     "Не отправленные напрямую музыкальные указания ("+missing.length+"):\n"+
     (missing.length?missing.map(x=>"• "+x.text).join("\n"):"Все приоритетные музыкальные указания уместились")+"\n\n"+
     "Звуки из промпта направлены в микшер: "+(styleFx.length?styleFx.join(", "):"нет новых или они уже указаны в тексте")+
     "\nФакт наличия инструкции в промпте не гарантирует её акустическое исполнение.";
   }catch(err){info.textContent="Ошибка проверки: "+err.message;}
  });
 }
});