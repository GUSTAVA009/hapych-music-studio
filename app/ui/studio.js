"use strict";

const $ = (id) => document.getElementById(id);
const pageTitles = {create:"Создать трек", voices:"Мой голос", tracks:"Библиотека", training:"Обучение моделей", settings:"Настройки"};
const presets = {
  modern808: "Modern melodic trap-pop, tuned sustained 808 sub-bass, tight punchy kick, dry snare and clap, crisp sparse hi-hat rolls, clean pluck hook, spacious pads, clear melodic lead vocal, controlled low end, clean contemporary mix. No lo-fi hiss, no vintage tape, no accordion.",
  oriental: "Весёлый русский рагга-рэп с восточными мотивами. Ритмичный танцевальный грув с дарбукой, сочным глубоким басом, чётким киком, сухим малым барабаном, запоминающийся рифф кларнета и уда, уверенная харизматичная мужская читка, припев с ясной мелодией, чистый мастеринг.",
  street: "Пацанский русский рэп с чёткой речитативной читкой. Хип-хоп грув, упругие барабаны с ясным акцентом бочки и рабочего, контролируемый 808 бас, короткие музыкальные перебивки, цепкий диалоговый припев, ироничная мужская подача, чистое современное сведение.",
  club: "Энергичный клубный хит с русским текстом. Плотный четырёхдольный танцевальный ритм, ясная бочка, воздушные хай-хэты, упругий сайдчейн-бас, яркий синтезаторный хук, чистый дроп с инструментальными переходами, короткий повторяющийся припев.",
  romantic: "Мелодичный русский поп-рэп, тёплый эмоциональный мужской вокал. Живая акустическая гитара, мягкий выразительный бас, ровные современные барабаны без резких перегрузок, просторный запоминающийся припев, выразительные динамические переходы."
};
let selectedVoice = "";
let selectedRemix = "";
let mode = "new";
let toastTimeout;
let oldResultSignature = "";

function notify(message, isError=false) {
  const el = $("toast");
  el.textContent = message;
  el.className = "toast" + (isError ? " error" : "");
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => el.classList.add("hidden"), 5500);
}
async function call(url, options={}) {
  const response = await fetch(url, {cache:"no-store", ...options});
  let data;
  try {data = await response.json();}
  catch {throw new Error("Нет ответа от локальной студии. Проверь запуск программы.");}
  if (!response.ok) throw new Error(data.error || ("Ошибка "+response.status));
  return data;
}
function navigate(page) {
  if (!pageTitles[page]) return;
  document.querySelectorAll(".page").forEach(x => x.classList.toggle("visible", x.id === "page-"+page));
  document.querySelectorAll(".nav-item").forEach(x => x.classList.toggle("active", x.dataset.page === page));
  $("crumb").textContent = pageTitles[page];
  if (page === "voices") refreshVoices();
  if (page === "tracks") refreshTracks();
  if(window.studio34OnNavigate) window.studio34OnNavigate(page);
  if (page === "training") refreshTraining();
  if (page === "settings") healthCheck();
  window.scrollTo({top:0,behavior:"smooth"});
}
document.querySelectorAll("[data-page]").forEach(x => x.addEventListener("click", () => navigate(x.dataset.page)));

function setMode(next) {
  mode = next;
  $("modeNew").classList.toggle("active", mode === "new");
  $("modeRemix").classList.toggle("active", mode === "remix");
  $("remixUploadArea").classList.toggle("hidden", mode !== "remix");
}
document.querySelectorAll("[data-mode]").forEach(x => x.addEventListener("click", () => setMode(x.dataset.mode)));
document.querySelectorAll("[data-preset]").forEach(x => x.addEventListener("click", () => {
  $("style").value = presets[x.dataset.preset];
  document.querySelectorAll(".chip").forEach(c => c.classList.toggle("selected", c === x));
  notify("Стиль добавлен. Можешь отредактировать его.");
}));
$("useVoice").addEventListener("change", () => {
  $("voiceChooser").classList.toggle("hidden", !$("useVoice").checked);
  if ($("useVoice").checked) refreshVoices();
});
$("voiceSelect").addEventListener("change", () => { selectedVoice = $("voiceSelect").value; });
$("instrumental").addEventListener("change", () => {
  $("lyrics").disabled = $("instrumental").checked;
  if ($("instrumental").checked) $("lyrics").placeholder = "Включён режим без вокала.";
  else $("lyrics").placeholder = "[Intro]\n[Verse 1]\nЗдесь слова твоего куплета...\n\n[Chorus]\nЗдесь мощный припев...";
  reviewWords();
});

function reviewWords() {
  const source = $("lyrics").value.replace(/\[[^\]]+\]/g, " ").trim();
  const words = source ? source.split(/\s+/).filter(Boolean).length : 0;
  $("wordCount").textContent = words + " слов";
  const duration = Number($("duration").value);
  const limit = duration === 0 ? 999999 : Math.round(duration*2.55);
  const warning = $("lengthAdvice");
  const hint = $("durationHint");
  if (hint) hint.textContent = duration === 0 ? "0 — ИИ сам определит длительность по тексту и структуре песни" : "Вручную: " + duration + " секунд";
  if (words > limit && !$("instrumental").checked) {
    warning.textContent = "⚠ В тексте " + words + " слов на " + duration + " сек. Модель может пропускать строки. Лучше сократить текст или увеличить длительность.";
    warning.classList.remove("hidden");
  } else warning.classList.add("hidden");
}
$("lyrics").addEventListener("input", reviewWords);
$("duration").addEventListener("change", reviewWords);
document.querySelectorAll("[data-insert]").forEach(button => button.addEventListener("click", () => {
  const box = $("lyrics");
  const at = box.selectionStart;
  const tag = button.dataset.insert;
  const before = box.value.slice(0, at);
  const after = box.value.slice(box.selectionEnd);
  const insertion = (before && !before.endsWith("\n") ? "\n\n" : "") + tag + "\n";
  box.value = before + insertion + after;
  box.focus();
  box.setSelectionRange(before.length + insertion.length, before.length + insertion.length);
  reviewWords();
}));

function element(tag, cls, text) {
  const el = document.createElement(tag);
  if (cls) el.className = cls;
  if (text !== undefined) el.textContent = text;
  return el;
}
function makeAsset(file, which) {
  const row = element("article","asset-row");
  const head = element("div","asset-head");
  const meta = element("div","asset-meta");
  const trackTitle = which === "tracks" ? element("button","track-open-title",file.title || file.name) : element("b","",file.title || file.name);
  if (which === "tracks") {
    trackTitle.type = "button";
    trackTitle.setAttribute("aria-label","Открыть карточку трека: "+(file.title || file.name));
    trackTitle.addEventListener("click", () => openTrackDetails(file));
    row.classList.add("track-openable");
    row.addEventListener("click", (event) => {
      if (!event.target.closest("audio,button,a,input,select,textarea")) openTrackDetails(file);
    });
  }
  meta.append(trackTitle, element("small","",file.when + " • "+(file.size/1048576).toFixed(1)+" МБ"));
  if(which==="tracks" && file.voice_check_status==="rejected")
    meta.append(element("small","voice-rejected","⚠ Твой голос не применён — сохранён исходный исполнитель"));
  else if(which==="tracks" && file.voice_applied===true)
    meta.append(element("small","voice-applied","✓ Запись твоего голоса применена"));
  if (which === "voices" && file.recording_warning) {
    meta.append(element("small","inline-note","⚠ "+file.recording_warning));
  }
  head.append(meta);
  row.append(head);
  const player = element("audio");
  player.controls = true;
  player.preload = "metadata";
  player.src = (which === "tracks" ? "/api/audio/" : "/api/voice/")+encodeURIComponent(file.name);
  if (which === "tracks") {
    const reveal = element("div","library-player hidden");
    reveal.append(player);
    const playButton = element("button","library-listen","▶ Слушать трек");
    playButton.type = "button";
    playButton.setAttribute("aria-expanded","false");
    playButton.addEventListener("click",() => {
      const isOpening = reveal.classList.contains("hidden");
      document.querySelectorAll("#tracksList .library-player:not(.hidden)").forEach(other => {
        if (other === reveal) return;
        other.classList.add("hidden");
        other.querySelector("audio")?.pause();
        const prior=other.previousElementSibling;
        if (prior && prior.classList.contains("library-listen")) {
          prior.textContent="▶ Слушать трек";
          prior.setAttribute("aria-expanded","false");
        }
      });
      reveal.classList.toggle("hidden",!isOpening);
      playButton.textContent=isOpening ? "▾ Свернуть плеер" : "▶ Слушать трек";
      playButton.setAttribute("aria-expanded",String(isOpening));
      if (isOpening) player.play().catch(() => {});
      else player.pause();
    });
    row.append(playButton,reveal);
  } else {
    row.append(player);
  }
  const acts = element("div","asset-actions");
  if (which === "voices") {
    const choose = element("button","secondary-button","Использовать в треке");
    choose.type = "button";
    choose.addEventListener("click", () => {
      selectedVoice = file.name;
      $("useVoice").checked = true;
      $("voiceChooser").classList.remove("hidden");
      navigate("create");
      $("voiceSelect").value = selectedVoice;
      notify("Референс выбран: " + file.name);
    });
    const remove = element("button","danger-button","Удалить запись");
    remove.type = "button";
    remove.addEventListener("click", async () => {
      if (!confirm("Удалить запись "+file.name+" с этого компьютера?")) return;
      try {
        await call("/api/remove_voice",{method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({name:file.name})});
        if (selectedVoice === file.name) selectedVoice = "";
        refreshVoices();
        notify("Запись удалена");
      } catch(e) { notify(e.message,true); }
    });
    acts.append(choose,remove);
  } else {
    const details = element("button","track-details-button","✦ Стиль и текст");
    details.type = "button";
    details.addEventListener("click", () => openTrackDetails(file));
    acts.append(details);
    const link = element("a","download-link","↓ Скачать MP3");
    link.href = "/api/audio/"+encodeURIComponent(file.name);
    link.download = file.name;
    acts.append(link);
    if (file.master_url) {
      const master=element("a","secondary-button","↓ WAV-мастер");
      master.href="/api/master/"+encodeURIComponent(file.name.replace(/\.mp3$/i,".wav"));
      master.download=file.name.replace(/\.mp3$/i,".wav"); acts.append(master);
    }
    if (file.original_url) {
      const original = element("a","secondary-button","↓ Исходная версия");
      original.href = file.original_url.slice(0,file.original_url.lastIndexOf("/")+1) + encodeURIComponent(file.original_name);
      original.download = file.original_name || "original.mp3";
      acts.append(original);
    }
  }
  row.append(acts);
  if (which === "tracks" && (file.fx_url || file.effects?.length || file.production_warnings?.length || file.learned_rhythm || file.sample_guided_808 || file.voice_check_note)) {
    const detail=element("details","track-meta-details");
    detail.append(element("summary","","Подробнее о генерации"));
    const inner=element("div","track-meta-content");
    appendProductionInfo(inner,inner,file);
    detail.append(inner);
    row.append(detail);
  }
  return row;
}
let trackDetailSequence=0;
async function openTrackDetails(file) {
  if(window.studio34OpenInspector) return window.studio34OpenInspector(file);
  const dialog=$("trackDetailDialog"), current=++trackDetailSequence;
  $("trackDetailTitle").textContent=file.title || file.name;
  $("trackDetailMeta").textContent=(file.when || "") + (file.variant ? " · Вариант "+file.variant : "");
  $("trackDetailStatus").textContent="Загружаем сохранённое задание...";
  ["trackDetailStyle","trackDetailModelCaption","trackDetailLyrics","trackDetailModelLyrics","trackDetailPlan"].forEach(id=>$(id).textContent="");
  if (!dialog.open) dialog.showModal();
  try {
    const info=await call("/api/track_details?name="+encodeURIComponent(file.name));
    if (current !== trackDetailSequence || !dialog.open) return;
    $("trackDetailTitle").textContent=info.title || file.name;
    $("trackDetailMeta").textContent="Вариант "+info.variant+" · "+(file.when || "")+" · "+info.status;
    $("trackDetailStatus").textContent=info.found ? "Показаны сохранённые данные этой генерации, не текущие поля редактора." : "Для этого старого трека описание стиля и текст не сохранились.";
    $("trackDetailStyle").textContent=info.style_original || "Исходное описание недоступно.";
    $("trackDetailModelCaption").textContent=info.model_caption || "Промпт музыкальной модели не сохранился.";
    $("trackDetailLyrics").textContent=info.lyrics_original || "Текст песни не сохранился.";
    $("trackDetailModelLyrics").textContent=info.lyrics_sent || "Текст для модели не сохранился.";
    const plan=info.style_plan || {};
    const notes=[];
    if (plan.genres?.length) notes.push("Жанры: "+plan.genres.join(", "));
    if (plan.instruments?.length) notes.push("Инструменты: "+plan.instruments.join(", "));
    if (plan.excluded?.length) notes.push("Исключения: "+plan.excluded.join(", "));
    if (plan.meter && plan.meter !== "auto") notes.push("Размер: "+plan.meter);
    if (plan.reference_policy === "trained_808") notes.push("Дополнительный ритм: обученная 808-модель");
    $("trackDetailPlan").textContent=notes.join("\n");
  } catch(error) {
    if (current===trackDetailSequence) $("trackDetailStatus").textContent="Ошибка открытия карточки: "+error.message;
  }
}
$("trackDetailClose").addEventListener("click",()=>$("trackDetailDialog").close());
$("trackDetailDialog").addEventListener("click",e=>{
  if(e.target===$("trackDetailDialog")) $("trackDetailDialog").close();
});

async function refreshVoices() {
  try {
    const d = await call("/api/voices");
    const select = $("voiceSelect"), list = $("voicesList");
    const existing = selectedVoice || select.value;
    select.replaceChildren();
    list.replaceChildren();
    if (!d.voices.length) {
      select.append(new Option("Сначала загрузи запись голоса",""));
      list.append(element("div","placeholder","Голосовых записей пока нет. Загрузи MP3 или WAV выше."));
    } else {
      select.append(new Option("Выбери запись голоса",""));
      d.voices.forEach(f => { select.append(new Option(f.name,f.name)); list.append(makeAsset(f,"voices")); });
      if (d.voices.some(v => v.name === existing)) select.value = existing;
      else if (d.voices.length === 1) select.value = d.voices[0].name;
      selectedVoice = select.value;
    }
  } catch(e) {notify(e.message,true);}
}
let libraryTracks = [], libraryPageSize = 12;
function renderLibrary() {
  const q = $("librarySearch").value.trim().toLocaleLowerCase("ru");
  const found = libraryTracks.filter(f => !q || (String(f.title || "")+" "+f.name+" "+(f.when || "")).toLocaleLowerCase("ru").includes(q));
  const visible = found.slice(0,libraryPageSize);
  const list=$("tracksList");
  list.replaceChildren();
  if(!found.length) list.append(element("div","placeholder",libraryTracks.length ? "По этому запросу треки не найдены." : "Здесь появятся песни после первой генерации."));
  else visible.forEach(f=>list.append(window.studio34MakeTrackRow ? window.studio34MakeTrackRow(f) : makeAsset(f,"tracks")));
  $("libraryCount").textContent = q ? "Найдено "+found.length+" из "+libraryTracks.length : "Показано "+visible.length+" из "+libraryTracks.length;
  const more=$("libraryMore");
  more.classList.toggle("hidden",visible.length>=found.length);
  more.textContent="Показать ещё · осталось "+Math.max(0,found.length-visible.length);
}
$("librarySearch").addEventListener("input",()=>{
  libraryPageSize=12;
  renderLibrary();
});
$("libraryMore").addEventListener("click",()=>{
  libraryPageSize+=12;renderLibrary();
});
let libraryFetchSerial=0;
async function refreshTracks() {
  const ticket=++libraryFetchSerial;
  try {
    const d=await call("/api/tracks");
    if (ticket!==libraryFetchSerial) return;
    libraryTracks=Array.isArray(d.tracks)?d.tracks:[];
    renderLibrary();
    if(window.studio34RenderFeed) window.studio34RenderFeed(libraryTracks);
  }catch(e){if(ticket===libraryFetchSerial) notify(e.message,true);}
}
async function uploadFile(file, kind) {
  if (!file) return;
  if (file.size > 90*1024*1024) { notify("Файл больше 90 МБ",true); return; }
  const endpoint = "/api/upload?kind="+encodeURIComponent(kind)+"&name="+encodeURIComponent(file.name);
  const text = kind === "voice" ? $("uploadStatus") : kind === "beat" ? $("beatUploadStatus") : $("remixHint");
  text.textContent = "Загружаем "+file.name+"...";
  try {
    const result = await call(endpoint, {method:"POST",headers:{"Content-Type":"application/octet-stream"},body:file});
    text.textContent = "✓ Загружено: "+file.name+" ("+(file.size/1048576).toFixed(1)+" МБ)";
    if (kind === "voice") {
      selectedVoice = result.name;
      await refreshVoices();
      notify("Запись добавлена. Теперь её можно выбрать для трека.");
    } else if (kind === "beat") {
      await refreshTraining();
      notify("Образец добавлен в локальный набор обучения. Система проверит готовность.");
    } else {
      selectedRemix = result.name;
      notify("Исходная песня готова для ремикса.");
    }
  } catch(e) {text.textContent = "Ошибка загрузки: "+e.message;notify(e.message,true);}
}
$("voiceFile").addEventListener("change", e => {if (e.target.files.length) uploadFile(e.target.files[0],"voice");});
$("remixFile").addEventListener("change", e => {if (e.target.files.length) uploadFile(e.target.files[0],"remix");});
const drop = $("voiceDrop");
drop.addEventListener("dragover", e => {e.preventDefault();drop.classList.add("dragging");});
drop.addEventListener("dragleave", () => drop.classList.remove("dragging"));
drop.addEventListener("drop", e => {
  e.preventDefault();
  drop.classList.remove("dragging");
  if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0],"voice");
});

async function createTrack() {
  const style = $("style").value.trim();
  const lyrics = $("lyrics").value.trim();
  if (!style) {navigate("create");$("style").focus();return notify("Заполни поле «Музыкальный стиль».",true);}
  if (!lyrics && !$("instrumental").checked) {navigate("create");$("lyrics").focus();return notify("Вставь текст песни или включи «Без вокала».",true);}
  if (mode === "remix" && !selectedRemix) return notify("Сначала загрузи исходную песню для ремикса.",true);
  if ($("useVoice").checked && !selectedVoice) return notify("Выбери запись голоса в разделе «Мой голос».",true);
  const bpm = Number($("bpm").value || 0);
  if (bpm !== 0 && (bpm < 30 || bpm > 300)) return notify("BPM должен быть от 30 до 300, либо 0.",true);
  $("generate").disabled = true;
  $("generate").textContent = "Подготавливаем генерацию...";
  const body = {
    title:$("title").value, style, lyrics, bpm, topic:$("songTopic").value,
    duration:Number($("duration").value), instrumental:$("instrumental").checked,
    vocal_language:"auto", vocal_gender:"auto",
    mode, source:selectedRemix, quality:"composer", use_voice:$("useVoice").checked, voice:selectedVoice, apply_voice:true, trained_voice:$("trainedVoice").checked, voice_register:$("voiceRegister").value, russian_rap:$("russianRap").checked, planner:$("planner").checked, producer:$("producer").checked, two_versions:$("twoVersions").checked
  };
  try {
    const prep = await call("/api/prepare",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    showTextPreparation(prep);
    await call("/api/generate",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    updateJob({status:"preparing",message:"Подготавливаем генерацию...",files:[],error:""});
    notify("Генерация запущена. Музыка появится справа.");
  } catch(e) {
    $("generate").disabled = false;
    $("generate").textContent = "✦ Создать мой трек →";
    notify(e.message,true);
  }
}
$("generate").addEventListener("click", createTrack);

function updateJob(job) {
  const busy = ["generating","preparing","converting"].includes(job.status) || Boolean(window.studioLyricsBusy);
  $("generate").disabled = busy;
  $("generate").textContent = busy ? "♫ Создаём трек..." : "✦ Создать мой трек →";
  const symbols = {idle:"♪",preparing:"⏳",generating:"♫",converting:"🎤",done:"✓",error:"!"};
  const titles = {idle:"Готов к генерации",preparing:"Подготовка",generating:"Идёт генерация",converting:"Перенос твоего голоса",done:"Песня готова!",error:"Ошибка генерации"};
  $("jobSymbol").textContent = symbols[job.status] || "♪";
  $("jobTitle").textContent = titles[job.status] || "Готов к генерации";
  $("jobDetails").textContent = job.status === "error" ? job.error || "Неизвестная ошибка" :
    job.status === "idle" ? "Вставь слова и стиль, затем нажми кнопку" : job.message || "";
  if(window.studio36OnJob)window.studio36OnJob(job);
  const files = Array.isArray(job.files) ? job.files : [];
  const signature = JSON.stringify(files.map(f => [f.name,f.cover_url,f.title]));
  if (signature !== oldResultSignature) {
    oldResultSignature = signature;
    const list = $("currentResults");
    list.replaceChildren();
    if (files.length && job.status === "done") {
      // Finished takes are real library entries, not extra bulky audio cards.
      // The shared bottom player and inspector handle playback and metadata.
      const message = element("p","studio35-done-note",
        "✓ "+files.length+" "+(files.length===1?"новый трек добавлен":"новых трека добавлены")+" в начало списка ↑");
      list.append(message);
      if (window.studio35RegisterGenerated) window.studio35RegisterGenerated(files);
      refreshTracks();
    }
  }
}
async function healthCheck() {
  try {
    const res = await call("/api/health");
    $("backendBadge").classList.toggle("offline",!res.ready);
    $("backendText").textContent = res.ready ? "Модель готова • RTX 4060" : "Модель загружается...";
    $("settingsEngine").textContent = res.ready ? "✓ Подключена" : "Инициализация...";
    window.studioLyricsBusy=Boolean(res.lyrics_busy);
    updateJob(res.job);
  } catch(e) {
    $("backendBadge").classList.add("offline");
    $("backendText").textContent = "Нет подключения";
  }
}
$("refreshTracks").addEventListener("click", refreshTracks);
$("checkEngine").addEventListener("click", healthCheck);
$("showLog").addEventListener("click", async () => {
  const area = $("logContent");
  if (!area.classList.contains("hidden")) {area.classList.add("hidden");return;}
  try {
    const data=await call("/api/log");
    area.textContent=data.text || "Ошибок нет.";
    area.classList.remove("hidden");
  } catch(e) {notify(e.message,true);}
});
window.addEventListener("error", e => notify("Ошибка интерфейса: "+e.message,true));
healthCheck();
refreshVoices();
reviewWords();
setInterval(healthCheck,5000);
async function refreshTraining() {
  try {
    const s = await call("/api/training");
    $("trainVoiceSamples").textContent = String(s.voice_samples) + " записей";
    $("trainVoiceSteps").textContent = s.voice_training_step + " / " + s.voice_training_total;
    $("trainVoiceReady").textContent = s.voice_checkpoint_ready ? "✓ Весовой файл модели сохранён" : "Нет завершённой модели";
    $("trainVoiceState").textContent = s.voice_training_message || "Готово к обучению";
    $("startVoiceTraining").disabled = Boolean(s.voice_training_running || s.voice_checkpoint_ready || s.voice_samples < 2);
    $("stopVoiceTraining").disabled = !s.voice_training_running;
    $("trainBeatCount").textContent = s.beat_samples + " из минимум " + s.beat_minimum;
    $("trainBeatReady").textContent = s.beat_training_ready ? "✓ Достаточно образцов для подготовки" : "Нужно больше качественных исходных треков";
  } catch (e) {
    notify("Не удалось проверить обучение: " + e.message, true);
  }
}
$("refreshTraining").addEventListener("click", refreshTraining);
$("startVoiceTraining").addEventListener("click", async () => {
  if (!confirm("Запустить донастройку голоса на RTX 4060? Пока она работает, создание песен будет временно недоступно.")) return;
  try {
    $("startVoiceTraining").disabled = true;
    await call("/api/train_voice", {method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});
    notify("Обучение собственного голоса началось.");
    await refreshTraining();
  } catch (e) { notify(e.message,true); await refreshTraining(); }
});
$("stopVoiceTraining").addEventListener("click", async () => {
  if (!confirm("Остановить обучение голоса? Несохранённые шаги будут потеряны.")) return;
  try {
    await call("/api/stop_voice_training", {method:"POST",headers:{"Content-Type":"application/json"},body:"{}"});
    notify("Обучение остановлено.");
    await refreshTraining();
  } catch(e) {notify(e.message,true);}
});
$("beatFile").addEventListener("change", e => {
  if (e.target.files.length) uploadFile(e.target.files[0], "beat");
});
setInterval(() => {
  if ($("page-training").classList.contains("visible")) refreshTraining();
}, 15000);


// Version 1.4: one server-side parser for preview and generation.
function preparationInput() {
  return {style:$("style").value, lyrics:$("lyrics").value,
    vocal_language:"auto", vocal_gender:"auto",
    instrumental:$("instrumental").checked, use_voice:$("useVoice").checked,
    trained_voice:$("trainedVoice").checked, russian_rap:$("russianRap").checked};
}
function showTextPreparation(p) {
  $("preparedCaption").value=p.caption;
  $("preparedLyrics").value=p.lyrics;
  $("styleCount").textContent="Описание: "+p.style_original_length+" → "+p.caption_length+" / 512 символов. Язык: "+p.vocal_language+".";
  const plan=p.style_plan || {};
  const genres=(plan.genres || []).join(", ") || "по описанию";
  $("prepSummary").textContent="Жанр: "+genres+". Инструменты: "+(plan.instruments || []).join(", ")+". Локальных указаний: "+p.directions.length+". Каждый тег действует на свой раздел.";
  $("preparedDirections").textContent=p.directions.map(d=>(d.section_id || d.section)+" / "+d.section+": "+d.text).join("\n") || "Отдельных указаний нет.";
  if(p.effects_plan?.length) $("preparedDirections").textContent += "\n\nОтдельные аудиодорожки:\n" + p.effects_plan.map(e=>e.section_id+" / "+e.section+": "+e.effect+(e.supported?" — сэмпл установлен":" — сэмпл не установлен")).join("\n");
  const removed=p.omitted.map(d=>"Не вошло: "+d.original);
  $("preparedWarnings").textContent=[...p.warnings,...removed].join("\n") || "Ограничения соблюдены. Отсутствие акцента оценивается по звучанию, а не по языковому коду.";
  // The detailed plan opens only when the user requests it.
}
let preparationTimer;
let preparationSequence=0;
async function previewText(showError=false) {
  const body=preparationInput();
  if(!body.style.trim()) return;
  const sequence=++preparationSequence;
  try {
    const p=await call("/api/prepare",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)});
    if(sequence===preparationSequence) showTextPreparation(p);
  } catch(e) {
    if(sequence===preparationSequence) $("styleCount").textContent=e.message;
    if(showError) notify(e.message,true);
  }
}
function queuePreparation() {
  clearTimeout(preparationTimer);
  $("styleCount").textContent="Исходное описание: "+Array.from($("style").value).length+" символов. Подготавливаем...";
  preparationTimer=setTimeout(()=>previewText(false),700);
}
["style","lyrics","vocalLanguage","vocalGender","instrumental","useVoice","russianRap"].forEach(id=>$(id).addEventListener("input",queuePreparation));
$("prepareText").addEventListener("click",()=>{$("prepDetails").open=true;previewText(true);});
$("loadTwoShores").addEventListener("click",async()=>{
  try {
    const p=await call("/api/presets/two-shores");
    ["title","style","lyrics","bpm","duration"].forEach(id=>$(id).value=p[id]);
    $("vocalLanguage").value=p.vocal_language;
    $("vocalGender").value=p.vocal_gender;
    $("useVoice").checked=false;$("trainedVoice").checked=false;$("russianRap").checked=false;
    $("instrumental").checked=false;$("lyrics").disabled=false;
    $("voiceChooser").classList.add("hidden");setMode("new");reviewWords();
    await previewText(true);
    notify("«Два берега»: русский женский вокал, 110 BPM, длительность автоматически. Исходные слова сохранены.");
  } catch(e) {notify(e.message,true);}
});

function appendProductionInfo(container,actions,item) {
  if(item.fx_url){const a=element("a","secondary-button","Отдельно: эффекты WAV");a.href="/api/fx/"+encodeURIComponent(item.fx_url.split("/").pop());a.download="";actions.append(a);}
  if(item.effects?.length) container.append(element("small","field-hint",item.effects.map(e=>e.effect+": "+e.start.toFixed(1)+"–"+e.end.toFixed(1)+" с").join("; ")));
  if(item.production_warnings?.length) container.append(element("p","inline-note",item.production_warnings.join(" ")));
  if(item.learned_rhythm) container.append(element("small","field-hint","Обученный ритм-модуль: использован при создании музыкального референса."));
  else if(item.sample_guided_808) container.append(element("small","field-hint","808: сэмпловый референс."));
  if(item.voice_check_note) container.append(element("p","inline-note",item.voice_check_note));
}

// Studio Motion 3.0: unobtrusive, user-controllable and GPU-light animation.
// Functional audio/model state stays in the existing application.
(function studioMotionInit(){
  const check=document.getElementById("motionEnabled");
  if(!check)return;
  let saved=null;
  try{saved=localStorage.getItem("musicStudio.motion");}catch(_){}
  const reduced=matchMedia("(prefers-reduced-motion: reduce)");
  let enabled=saved==="off"?false:saved==="on"?true:!reduced.matches;
  function setMotion(value,persist){
    enabled=Boolean(value);
    document.documentElement.classList.toggle("motion-disabled",!enabled);
    check.checked=enabled;
    if(persist){try{localStorage.setItem("musicStudio.motion",enabled?"on":"off");}catch(_){}}
  }
  setMotion(enabled,false);
  check.addEventListener("change",()=>setMotion(check.checked,true));
  reduced.addEventListener?.("change",()=>{
    try{if(!localStorage.getItem("musicStudio.motion"))setMotion(!reduced.matches,false);}catch(_){}
  });
  const job=document.getElementById("jobBox");
  const title=document.getElementById("jobTitle");
  const gen=document.getElementById("generate");
  const wave=document.createElement("div");
  wave.className="ms-status-wave";wave.setAttribute("aria-hidden","true");
  for(let i=0;i<7;i++){
    const bar=document.createElement("i");
    bar.style.setProperty("--eq-index",String(i));
    wave.appendChild(bar);
  }
  job.appendChild(wave);
  const syncBusy=()=>{
    const titleText=title.textContent.toLocaleLowerCase("ru");
    const working=Boolean(gen.disabled) && /подготов|генерац|перенос|созда/.test(titleText);
    document.documentElement.classList.toggle("studio-generating",working);
    job.setAttribute("aria-busy",String(working));
  };
  new MutationObserver(syncBusy).observe(title,{childList:true,subtree:true,characterData:true});
  new MutationObserver(syncBusy).observe(gen,{attributes:true,attributeFilter:["disabled"]});
  syncBusy();
  for(const id of ["tracksList","voicesList"]){
    const list=document.getElementById(id);
    if(!list)continue;
    const animateChildren=()=>{
      list.querySelectorAll(":scope > .asset-row").forEach((node,index)=>{
        node.classList.add("ms-enter");
        node.style.setProperty("--ms-list-index",String(index));
      });
    };
    new MutationObserver(animateChildren).observe(list,{childList:true});
    animateChildren();
  }
})();
