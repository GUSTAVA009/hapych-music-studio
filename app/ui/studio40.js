"use strict";
(() => {
  const $=id=>document.getElementById(id);
  const mk=(tag,cls,txt)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(txt!==undefined)e.textContent=txt;return e};
  const card=document.querySelector("#page-settings .studio38-storage-card");
  if(card){
    const old=card.querySelector(".studio38-storage-records");
    const records=mk("div","studio40-storage-records");
    const notice=mk("p","studio40-folder-note","Все папки находятся на твоём компьютере. Скачивание MP3 по-прежнему доступно в библиотеке.");
    card.insertBefore(records,old);
    old?.remove();
    const choices=[["tracks","Готовые треки"],["covers","Обложки"],["voices","Мои голосовые записи"],
       ["originals","Исходники"],["masters","Мастер WAV"],["trash","Корзина"],["exports","Экспорт"]];
    fetch("/api/settings/storage").then(r=>r.json()).then(data=>{
      records.replaceChildren();
      for(const [kind,title] of choices){
        const path=data.paths?.[kind];
        if(!path)continue;
        const row=mk("div","studio40-storage-item");
        const text=mk("div","studio40-storage-location");
        text.append(mk("strong","",title),mk("small","",path));
        const actions=mk("div","studio40-storage-actions");
        const open=mk("button","secondary-button","Открыть");
        open.type="button";
        open.addEventListener("click",async()=>{
          try{
            const response=await fetch("/api/open-folder",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({kind})});
            const data=await response.json();
            if(!response.ok)throw Error(data.error||"Не удалось открыть папку");
          }catch(e){alert(e.message)}
        });
        const copy=mk("button","secondary-button","Копировать путь");
        copy.type="button";
        copy.addEventListener("click",()=>navigator.clipboard.writeText(path).then(()=>copy.textContent="Скопировано").catch(()=>alert(path)));
        actions.append(open,copy);row.append(text,actions);records.append(row);
      }
    }).catch(()=>records.append(mk("p","","Не удалось загрузить локальные директории.")));
    card.append(notice);
  }
  const hint=mk("p","studio40-style-hint","Жанр имеет приоритет. Даже длинное описание сохраняется целиком — движку передаются главные указания до 512 символов.");
  $("style")?.closest(".studio37-style-card")?.append(hint);
  // A real preview of the exact server-generated caption is already shown by
  // /api/prepare; never impose a 512-character limit on user input.
  $("style")?.removeAttribute("maxlength");
  // Render cover regeneration in the existing inspector, preserving song player.
  const details=$("studio34InspectorMore");
  const rerender=mk("button","studio40-redraw-button","↻ Перегенерировать обложку по песне");
  rerender.type="button";rerender.hidden=true;
  const state=mk("span","studio40-cover-state");
  // The inspector replaces its dynamic download links on every selection.
  // Keep the cover action in a stable sibling instead of that replaced slot.
  details?.after(rerender,state);
  const inspector=$("studio34Inspector");
  const update=()=>{
    const title=$("studio34InspectorTitle")?.textContent||"";
    const active=document.querySelector(".studio34-track-row.selected");
    const name=active?.dataset.filename||"";
    rerender.hidden=!name;
    rerender.dataset.name=name;
    state.textContent="";
  };
  if(inspector)new MutationObserver(update).observe(inspector,{attributes:true,attributeFilter:["class"]});
  rerender.addEventListener("click",async()=>{
    const name=rerender.dataset.name;
    if(!name)return;
    rerender.disabled=true;state.textContent="Обложка поставлена в очередь…";
    try{
      const response=await fetch("/api/regenerate-cover",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({name})});
      const result=await response.json();
      if(!response.ok||!result.ok)throw Error(result.error||"Модель обложек пока не готова");
      state.textContent="Создаём изображение. Музыка доступна сразу.";
      let attempts=0;
      const check=setInterval(async()=>{
        try{
          const resp=await fetch("/api/cover_status?name="+encodeURIComponent(name));
          const info=await resp.json();attempts++;
          if(info.status==="ready"){
            clearInterval(check);state.textContent="Новая обложка готова.";
            document.querySelectorAll(".studio35-cover-image").forEach(img=>{
              if(img.src.includes("/api/cover/"+encodeURIComponent(name))){
                img.src="/api/cover/"+encodeURIComponent(name)+"?v="+Date.now();
              }
            });
            rerender.disabled=false;
          }else if(attempts>50){
            clearInterval(check);rerender.disabled=false;state.textContent="Проверь статус позднее.";
          }
        }catch(e){clearInterval(check);rerender.disabled=false;state.textContent="Ошибка проверки обложки";}
      },4000);
    }catch(e){state.textContent=e.message;rerender.disabled=false}
  });
})();
