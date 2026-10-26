"use strict";
document.addEventListener("DOMContentLoaded",()=>{
  const configs=[{id:"songWords",text:"Импорт TXT / MD",max:24000},
                 {id:"songStyle",text:"Импорт промпта",max:12000}];
  for(const cfg of configs){
    const editor=document.getElementById(cfg.id);
    const label=document.querySelector('label[for="'+cfg.id+'"]');
    if(!editor||!label)continue;
    const header=label.closest(".field-heading");
    if(!header)continue;
    const button=document.createElement("button");
    button.type="button";button.className="small-action";
    button.textContent=cfg.text;button.title="Загрузить текст из файла без удаления существующих песен";
    const input=document.createElement("input");
    input.type="file";input.accept=".txt,.md,.text,text/plain,text/markdown";
    input.hidden=true;input.setAttribute("aria-label",cfg.text);
    header.insertBefore(button,header.querySelector(".info-button")||null);
    header.appendChild(input);
    button.addEventListener("click",()=>input.click());
    async function loadFile(file){
      if(!file)return;
      if(file.size>200000){window.alert("Файл слишком большой: максимум 200 КБ.");return;}
      try{
        let text=await file.text();
        text=text.replace(/^\uFEFF/,"").replace(/\r\n?/g,"\n");
        if(!text.trim())throw new Error("В файле нет текста");
        if(text.length>cfg.max)throw new Error("Текст длиннее лимита загрузки ("+cfg.max+" символов). Сократи документ или раздели песню.");
        editor.value=text.trim();
        editor.dispatchEvent(new Event("input",{bubbles:true}));
        editor.dispatchEvent(new Event("change",{bubbles:true}));
        const feedback=document.getElementById(cfg.id+"ImportStatus")||document.createElement("span");
        feedback.id=cfg.id+"ImportStatus";feedback.className="muted";
        feedback.style.fontSize="12px";feedback.textContent="Загружено: "+file.name;
        if(!feedback.isConnected)header.appendChild(feedback);
      }catch(err){window.alert("Не удалось импортировать текст: "+err.message);}
    }
    input.addEventListener("change",async()=>{await loadFile(input.files?.[0]);input.value="";});
    editor.addEventListener("dragover",e=>{if(e.dataTransfer?.types?.includes("Files"))e.preventDefault();});
    editor.addEventListener("drop",e=>{if(e.dataTransfer?.files?.length){e.preventDefault();void loadFile(e.dataTransfer.files[0]);}});
  }
});