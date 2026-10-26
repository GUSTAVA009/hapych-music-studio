"use strict";
/* Composer 3.2 — presentation-only status, no generation, model or persistence changes. */
(() => {
  const byId=id=>document.getElementById(id);
  const style=byId("style");
  const lyrics=byId("lyrics");
  const instrumental=byId("instrumental");
  const useVoice=byId("useVoice");
  const voice=byId("voiceSelect");
  const stateNodes=[
    byId("composeCheckStyle"),
    byId("composeCheckLyrics"),
    byId("composeCheckVoice")
  ];
  if(!style||!lyrics||stateNodes.some(x=>!x))return;

  const setState=(node,done,label)=>{
    node.classList.toggle("done",Boolean(done));
    const mark=node.querySelector(".compose-check-mark");
    const text=node.querySelector(".status-text");
    if(mark)mark.textContent=done?"✓":node===stateNodes[0]?"1":node===stateNodes[1]?"2":"3";
    if(text)text.textContent=label;
  };

  const notice=byId("chosenLyricLabel");
  function sync(){
    const described=style.value.trim().length>=8;
    const hasText=lyrics.value.trim().length>0;
    const noWords=instrumental.checked;
    const voiceEnabled=useVoice.checked;
    const voiceSelected=voiceEnabled&&Boolean(voice.value);

    setState(stateNodes[0],described,described?"Добавлен":"Не заполнен");
    setState(stateNodes[1],noWords||hasText,noWords?"Инструментал":hasText?"Добавлен":"Не заполнен");
    setState(stateNodes[2],voiceSelected,voiceEnabled?(voiceSelected?"Запись выбрана":"Выбери запись"):"По желанию");

    // Old draft text was misleading: it claimed no lyrics were selected when
    // the editable editor already held complete lyrics. Keep specific selected
    // variant messages written by the main workflow.
    if(notice){
      const v=notice.textContent.trim();
      if(v.startsWith("Ни один вариант пока не выбран.") ||
         v.startsWith("Вставь текст песни или")) {
        notice.textContent=hasText
          ?"Текст в редакторе можно менять — изменения войдут в новую генерацию."
          :"Вставь свой текст или нажми «Сгенерировать текст».";
      }
    }
  }
  [style,lyrics].forEach(el=>el.addEventListener("input",sync));
  [instrumental,useVoice,voice].forEach(el=>el.addEventListener("change",sync));
  document.querySelectorAll("[data-preset],#loadTwoShores,[data-insert]").forEach(el=>
    el.addEventListener("click",()=>queueMicrotask(sync))
  );
  // UI may rehydrate the selected voice and saved lyrics asynchronously.
  const observer=new MutationObserver(()=>{
    if(!byId("page-create").classList.contains("visible"))return;
    sync();
  });
  observer.observe(voice,{childList:true});
  const quick=byId("generateQuick"), original=byId("generate"), versions=byId("twoVersions");
  if(quick && original){
    const alignPrimary=()=>{
      quick.disabled=original.disabled;
      if(byId("quickGenerateLabel")){
        byId("quickGenerateLabel").textContent=original.disabled
          ? "Генерация выполняется..."
          : (versions?.checked?"Создать 2 варианта":"Создать песню");
      }
    };
    quick.addEventListener("click",()=>{
      if(!original.disabled)original.click();
    });
    versions?.addEventListener("change",alignPrimary);
    new MutationObserver(alignPrimary).observe(original,{attributes:true,attributeFilter:["disabled"]});
    alignPrimary();
  }
  sync();
  document.addEventListener("visibilitychange",()=>{
    if(!document.hidden)sync();
  });
})();
