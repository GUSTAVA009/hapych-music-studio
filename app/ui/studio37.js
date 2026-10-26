"use strict";
/* Music Studio 3.7: carefully reorganize existing bound controls.
   No change to the music model, generation, recordings or storage.
*/
(() => {
  const $=id=>document.getElementById(id);
  const editor=document.querySelector("#page-create .editor-panel");
  const cards=Array.from(editor?.children||[]).filter(el=>el.classList.contains("card"));
  if(cards.length!==4)return;
  const [titleCard,styleCard,lyricCard,voiceCard]=cards;
  const make=(tag,cls,text)=>{
    const el=document.createElement(tag);
    if(cls)el.className=cls;
    if(text!==undefined)el.textContent=text;
    return el;
  };

  // Put the primary creative activity first.
  const toolbar=make("div","studio37-composer-toolbar");
  const modes=make("div","studio37-mode-switch");
  modes.setAttribute("role","group");
  modes.setAttribute("aria-label","Тип композиции");
  const song=make("button","studio37-mode","Песня");
  const instrumental=make("button","studio37-mode","Инструментал");
  for(const b of [song,instrumental]){b.type="button";b.setAttribute("aria-pressed","false");}
  modes.append(song,instrumental);
  const quick=make("div","studio37-quick-tools");
  const audio=make("button","studio37-tool","＋ Аудио");
  const voice=make("button","studio37-tool","＋ Мой голос");
  const prefs=make("button","studio37-tool studio37-tool-more","Настройки");
  for(const b of [audio,voice,prefs])b.type="button";
  quick.append(audio,voice,prefs);
  toolbar.append(modes,quick);
  const extras=make("details","studio37-extras");
  extras.id="studio37Extras";
  const summary=make("summary","studio37-extras-head");
  summary.append(make("span","","Дополнительные настройки"),
    make("span","studio37-extras-chevron","⌄"));
  extras.append(summary);
  const extrasInner=make("div","studio37-extras-body");
  extras.append(extrasInner);
  extrasInner.append(titleCard,voiceCard);

  editor.insertBefore(toolbar,editor.firstChild);
  editor.insertBefore(lyricCard,editor.querySelector(".compose-run"));
  editor.insertBefore(styleCard,editor.querySelector(".compose-run"));
  editor.insertBefore(extras,editor.querySelector(".compose-run"));
  // Dedicated creation footer below the scroller: the main action no
  // longer overlays the text, style field, or settings at any viewport.
  const generateButton=$("generateQuick");
  const editorShell=make("div","studio37-editor-shell");
  editor.parentNode.insertBefore(editorShell,editor);
  editorShell.append(editor);
  const footer=make("div","studio37-run-footer");
  editorShell.append(footer);
  footer.append(generateButton);

  titleCard.classList.add("studio37-title-card");
  styleCard.classList.add("studio37-style-card");
  lyricCard.classList.add("studio37-lyrics-card");
  voiceCard.classList.add("studio37-voice-card");
  editor.classList.add("studio37-editor");

  const instrumentalInput=$("instrumental"),voiceInput=$("useVoice");
  function syncModes(){
    const selected=!!instrumentalInput?.checked;
    song.classList.toggle("active",!selected);
    instrumental.classList.toggle("active",selected);
    song.setAttribute("aria-pressed",String(!selected));
    instrumental.setAttribute("aria-pressed",String(selected));
    lyricCard.classList.toggle("studio37-instrumental",selected);
    voice.classList.toggle("active",!!voiceInput?.checked);
    audio.classList.toggle("active",$("modeRemix")?.classList.contains("active")||false);
  }
  song.addEventListener("click",()=>{
    if(instrumentalInput.checked)instrumentalInput.click();
    syncModes();
  });
  instrumental.addEventListener("click",()=>{
    if(!instrumentalInput.checked)instrumentalInput.click();
    syncModes();
  });
  instrumentalInput?.addEventListener("change",syncModes);
  voiceInput?.addEventListener("change",syncModes);
  function revealExtras(node){
    extras.open=true;
    if(node)requestAnimationFrame(()=>node.scrollIntoView({block:"nearest",behavior:"smooth"}));
  }
  audio.addEventListener("click",()=>{
    revealExtras(titleCard);
    const remixDetails=titleCard.querySelector("details.remix-details");
    if(remixDetails)remixDetails.open=true;
    const remix=$("modeRemix");
    if(remix&&!remix.classList.contains("active"))remix.click();
    syncModes();
  });
  voice.addEventListener("click",()=>{
    if(!voiceInput.checked)voiceInput.click();
    revealExtras(voiceCard);
    syncModes();
  });
  prefs.addEventListener("click",()=>{
    revealExtras(voiceCard);
    const advanced=voiceCard.querySelector("details.advanced-song");
    if(advanced)advanced.open=true;
    advanced?.scrollIntoView({block:"nearest",behavior:"smooth"});
  });
  if(voiceInput?.checked||$("modeRemix")?.classList.contains("active"))extras.open=true;
  document.querySelectorAll("[data-mode]").forEach(b=>b.addEventListener("click",syncModes));
  syncModes();

  // Reduce editor chrome, without removing functions: three section tags
  // and producer helpers remain available behind native disclosures.
  function disclosure(label,block,cls){
    if(!block)return;
    const box=make("details",cls);
    const head=make("summary","studio37-disclosure-summary",label);
    block.parentNode.insertBefore(box,block);
    box.append(head,block);
    return box;
  }
  const sectionActions=lyricCard.querySelector(".lyric-actions");
  disclosure("＋ Раздел песни",sectionActions,"studio37-section-tools");
  const quickStyles=styleCard.querySelector("#presetChips");
  if(quickStyles){
    const presetsLabel=styleCard.querySelector(".presets-label");
    const preparation=styleCard.querySelector(".preparation-actions");
    const prepDetails=styleCard.querySelector("#prepDetails");
    const shell=make("div","studio37-production-tools-body");
    const producer=make("details","studio37-production-tools");
    producer.append(make("summary","studio37-disclosure-summary","Быстрые стили и проверка промпта"),shell);
    if(presetsLabel?.parentNode)presetsLabel.parentNode.insertBefore(producer,presetsLabel);
    for(const node of [presetsLabel,quickStyles,preparation,prepDetails])if(node)shell.append(node);
  }
  // Keep HTML labels programmatically associated with the two native textareas.
  // This only reduces redundant visible captions.
  for(const [card,id] of [[lyricCard,"lyrics"],[styleCard,"style"]]){
    card.querySelector('label[for="'+id+'"]')?.classList.add("studio37-visually-hidden");
  }

  const feed=$("page-create")?.querySelector(".studio34-feed");
  const search=feed?.querySelector(".studio34-search");
  if(search){
    const tools=make("div","studio37-list-tools");
    const sort=make("select","studio37-sort");
    sort.id="studio37Sort";
    sort.setAttribute("aria-label","Сортировка композиций");
    [
      ["newest","Сначала новые"],
      ["oldest","Сначала старые"],
      ["title","По названию"]
    ].forEach(([value,label])=>{
      const option=make("option","",label);
      option.value=value;sort.append(option);
    });
    tools.append(sort);
    search.insertAdjacentElement("afterend",tools);
    window.studio37FeedSort="newest";
    sort.addEventListener("change",()=>{
      window.studio37FeedSort=sort.value;
      $("studio34CreateSearch")?.dispatchEvent(new Event("input"));
    });
  }

  // On desktop dock the inspector without covering the library.
  const inspector=$("studio34Inspector");
  function syncInspector(){
    document.body.classList.toggle("studio37-inspector-open",!!inspector?.classList.contains("open"));
  }
  if(inspector){
    new MutationObserver(syncInspector).observe(inspector,{attributes:true,attributeFilter:["class"]});
    syncInspector();
  }

  // Readability and keyboard-friendly row actions.
  const lists=[$("studio34FeedList"),$("tracksList")].filter(Boolean);
  function makeReadable(){
    for(const list of lists){
      list.querySelectorAll(".studio34-track-row").forEach(row=>{
        if(row.classList.contains("studio37-ready"))return;
        row.classList.add("studio37-ready");
      });
    }
  }
  lists.forEach(el=>new MutationObserver(makeReadable).observe(el,{childList:true}));
  makeReadable();
  const heading=feed?.querySelector(".studio34-feed-title h2");
  if(heading)heading.textContent="Твои композиции";
})();
