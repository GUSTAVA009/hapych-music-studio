/* QA76: explicit user-operated sung-voice dataset collection guide.
   No automatic training, uploading outside localhost, or identity assumptions.
   Stage completion is a self-reported checklist, NOT verified audio. */
"use strict";
document.addEventListener("DOMContentLoaded",()=>{
 const page=document.getElementById("view-voices");
 if(!page || document.getElementById("singingTraining76"))return;
 const stages=[
  {id:"low_legato",title:"01 · Низкий регистр / длинные гласные",length:"90–110 секунд",type:"sing",
   prompt:"А-а-а-а… О-о-о-о… У-у-у-у… Э-э-э-э… И-и-и-и… Ы-ы-ы-ы…\nСпой каждую гласную плавно 5–8 секунд на удобной низкой ноте. Между нотами — короткий вдох. Повтори круг четыре раза. Без вибрато и напряжения."},
  {id:"low_lines",title:"02 · Низкий регистр / фразы",length:"80–110 секунд",type:"sing",
   prompt:"Ночь на ладонях, фонари в окнах.\nТёплый ветер с нами говорит.\nЯ не стану слова торопить,\nПусть дорога долго-долго длится.\nПовторяй спокойно в нижнем удобном регистре. Не обрывай окончания слов."},
  {id:"middle_legato",title:"03 · Средний регистр / протяжные ноты",length:"80–110 секунд",type:"sing",
   prompt:"А-а-а, О-о-о, И-и-и, Е-е-е.\nСвет в твоём окне горит.\nУтро тихо говорит.\nДороги нас ведут домой.\nПой в среднем удобном регистре связно, без речитатива. Одну гласную держи 4–6 секунд."},
  {id:"register_glide",title:"04 · Плавные переходы между регистрами",length:"80–100 секунд",type:"sing",
   prompt:"А-а-а-а-а: плавно снизу вверх и обратно без скачка.\nО-о-о-о-о: так же, но спокойнее.\nЛадони тёплые, дороги долгие.\nВ окнах гаснет свет, но сердце говорит.\nПой без напряжения и форсирования высоты. Не делай искусственное вибрато."},
  {id:"russian_phonemes",title:"05 · Русские согласные и окончания",length:"80–110 секунд",type:"sing",
   prompt:"Ладонях — дорогах — окнах — горит.\nТепло — торопить — слова — любовь.\nШироко — шёлк — дождь — рожь — жизнь.\nРядом — родной — горы — ровно — тихо.\nНапевай на одной удобной ноте и с естественным русским произношением. Повтори с разной громкостью без крика."},
  {id:"dynamic_phrase",title:"06 · Динамика / мягкость / дыхание",length:"80–110 секунд",type:"sing",
   prompt:"Я узнаю твои шаги,\nСвет на ладонях береги.\nПускай дороги далеко,\nС тобой мне дышится легко.\nПой по три раза: тихо, средне и уверенно. Сохраняй мягкие окончания и паузы на дыхание. Не шепчи."},
  {id:"rhythmic_rap",title:"07 · Русский рэп / ритмичные согласные",length:"80–110 секунд",type:"sing",
   prompt:"Город не спит, барабаны стучат,\nПоворот за поворотом, фонари горят.\nСлова на бит ложатся чётко в такт,\nИ каждый звук идёт вперёд, а не назад.\nПрочитай ритмично на одном выдохе, потом напевно. Без фоновой музыки и метронома в микрофоне."},
  {id:"melodic_chorus",title:"08 · Припев / мелодичное непрерывное пение",length:"80–110 секунд",type:"sing",
   prompt:"Я тебя не ищу, но помню,\nКак шумит осенний сад.\nВетер улицы наполнит,\nИ слова назад летят.\nСпой весь четверостишный припев единым движением, с плавными переходами в удобном диапазоне. Повтори 3–4 раза с короткими паузами."},
  {id:"heldout",title:"09 · Контрольная запись — НЕ для обучения",length:"60–90 секунд",type:"sing",
   prompt:"Я смотрю в открытое окно,\nТихо утро унесёт тепло.\nПусть горят огни на берегу,\nЯ слова спокойно сберегу.\nСпой этот текст только сейчас, естественно и без форсирования. Это независимая проверка. В тренировочный набор не добавлять."}
 ];
 const key="musicstudio76.sungStages.selfReported";
 let done={};
 try{const value=JSON.parse(localStorage.getItem(key)||"{}");if(value&&typeof value==="object")done=value;}catch{}
 let current=0;
 const style=document.createElement("style");
 style.textContent=".sing76{margin-top:18px;padding:20px;border:1px solid #34394b;border-radius:16px;background:#171a22;color:#eef0f7}.sing76 h2{margin:0 0 9px;font-size:20px}.sing76 p{line-height:1.5}.sing76 .muted{color:#aeb6c7}.sing76-controls{display:flex;flex-wrap:wrap;align-items:center;gap:10px}.sing76 select{width:min(100%,500px);background:#202431;border:1px solid #525971;color:#f5f5ff;border-radius:9px;padding:10px;font:inherit}.sing76 button{cursor:pointer;border-radius:9px;padding:10px 14px;border:1px solid #747e97;color:#fff;background:#333a4b;font:inherit}.sing76 button.sing76-go{background:#8368db;border-color:#8368db}.sing76 blockquote{margin:14px 0;padding:14px;border-left:3px solid #9f86fb;background:#222637;border-radius:7px;white-space:pre-wrap;line-height:1.65;color:#eff0f8}.sing76-progress{font-weight:600;color:#cdbdff}.sing76-status{min-height:1em;font-size:13px;color:#aeb6c7}.sing76-check{display:flex;align-items:center;gap:8px;padding:6px 0}.sing76-check input{width:18px;height:18px;accent-color:#9070e7}.sing76-small{font-size:13px}";
 document.head.appendChild(style);
 const card=document.createElement("section");card.id="singingTraining76";card.className="sing76";
 card.innerHTML='<h2>🎙️ Материал для обучения певческого тембра</h2>'+
 '<p class="muted">Текущих коротких разговорных образцов недостаточно для устойчивого персонального пения. Собери примерно 12–16 минут <b>своего чистого вокала</b>, отдельными файлами. Это подготовка датасета, а не кнопка автоматического переобучения.</p>'+
 '<div class="sing76-controls"><label for="sing76Step">Этап записи</label><select id="sing76Step" aria-label="Выбрать этап записи"></select><span id="sing76Progress" class="sing76-progress" aria-live="polite"></span></div>'+
 '<p id="sing76Length" class="sing76-small muted"></p><blockquote id="sing76Script"></blockquote>'+
 '<div class="sing76-controls"><button type="button" id="sing76Record" class="sing76-go">Записать этот этап</button><button type="button" id="sing76Copy">Копировать текст</button></div>'+
 '<label class="sing76-check"><input type="checkbox" id="sing76Done"> Я сохранил файл этого этапа (отметка вручную)</label>'+
 '<p class="sing76-small muted">Записывай один голос, без реверберации, автотюна, фоновой музыки, других людей или чужих вокалов. Не напрягай связки. Сохраняй русские согласные и окончания. Записи не публикуются через этот модуль; студия сохраняет их локально.</p>'+
 '<p class="sing76-small muted">Рекордер автоматически завершает отдельный дубль примерно через 125 секунд. Контрольный этап 09 должен быть исключён из обучающего набора и нужен только для независимой проверки.</p>'+
 '<p id="sing76Status" class="sing76-status" role="status"></p>';
 page.appendChild(card);
 const $=id=>document.getElementById(id);
 for(let i=0;i<stages.length;i++){const el=document.createElement("option");el.value=String(i);el.textContent=stages[i].title; $("sing76Step").appendChild(el);}
 function refresh(){
  const s=stages[current];$("sing76Step").value=String(current);
  $("sing76Script").textContent=s.prompt;
  $("sing76Length").textContent="Ориентир: "+s.length+(current===8?" • Только контроль, не обучать":"");
  $("sing76Done").checked=Boolean(done[s.id]);
  $("sing76Progress").textContent=stages.filter(x=>done[x.id]).length+"/"+stages.length+" этапов отмечено";
  $("sing76Status").textContent="Отметки показывают только твой прогресс и не подтверждают наличие обучающих WAV.";
 }
 $("sing76Step").addEventListener("change",()=>{current=Number($("sing76Step").value)||0;refresh();});
 $("sing76Done").addEventListener("change",()=>{
  done[stages[current].id]=$("sing76Done").checked;
  try{localStorage.setItem(key,JSON.stringify(done));}catch{}
  refresh();
 });
 $("sing76Copy").addEventListener("click",async()=>{
  try{await navigator.clipboard.writeText(stages[current].prompt);$("sing76Status").textContent="Текст скопирован.";}
  catch{$("sing76Status").textContent="Копирование недоступно. Выдели текст вручную.";}
 });
 $("sing76Record").addEventListener("click",()=>{
  const open=$("addVoice"),kind=$("voiceKind"),lang=$("voiceLang"),sample=$("voiceSample");
  if(!open||!kind||!lang||!sample){$("sing76Status").textContent="Мастер записи голоса недоступен.";return;}
  window.studioTraining76Active={id:stages[current].id,heldout:current===8};
  lang.value="ru";kind.value="sing";
  open.click();
  kind.dispatchEvent(new Event("change",{bubbles:true}));
  sample.textContent=stages[current].prompt;
  $("sing76Status").textContent="Мастер записи открыт. Сохрани этот дубль с твоим существующим профилем исполнителя.";
 });
 document.addEventListener("studioTraining76:saved",ev=>{
  const id=String(ev.detail?.id||"");
  if(!stages.some(s=>s.id===id))return;
  done[id]=true;
  try{localStorage.setItem(key,JSON.stringify(done));}catch{}
  const name=String(ev.detail?.filename||"");
  $("sing76Status").textContent="Запись этапа сохранена: "+name+(id==="heldout"?" · контроль, не добавляй в обучение":"");
  refresh();
  $("sing76Status").textContent="Запись этапа сохранена: "+name+(id==="heldout"?" · контроль, не добавляй в обучение":"");
 });
 refresh();
});
