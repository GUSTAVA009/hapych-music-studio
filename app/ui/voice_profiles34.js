"use strict";
document.addEventListener("DOMContentLoaded",()=>{
 const $=id=>document.getElementById(id);
 const voiceSelect=$("voiceSelect"), params=$("paramsVoice"),wizard=$("voiceStep1");
 if(!voiceSelect||!params||!wizard)return;
 const css=document.createElement("style");
 css.textContent=[
 ".v34-panel{padding:12px;border:1px solid #424552;border-radius:12px;background:#1e2027;margin:12px 0;display:grid;gap:9px}",
 ".v34-panel label{display:grid;gap:5px;font-size:13px;color:#ddd}",
 ".v34-panel select,.v34-panel input{width:100%;background:#151820;color:#fff;border:1px solid #525969;padding:9px;border-radius:8px;min-width:0}",
 ".v34-row{display:flex;gap:9px;align-items:center;flex-wrap:wrap}",
 ".v34-row button{padding:8px 12px;border:1px solid #6c69a8;border-radius:8px;background:#4f4690;color:#fff;cursor:pointer}",
 ".v34-note{font-size:12px;color:#b9bcc9;line-height:1.45}",
 ".v34-panel .v34-own{display:flex;align-items:center;gap:8px}",
 ".v34-panel .v34-own input{width:17px;height:17px}"
 ].join("");
 document.head.appendChild(css);
 const panel=document.createElement("section");panel.className="v34-panel";
 panel.innerHTML='<strong>Профиль исполнителя</strong>'+
 '<p class="v34-note">Разные артисты хранятся отдельно. Одна запись может принадлежать только одному исполнителю. Общие обученные веса для всех людей не используются.</p>'+
 '<label>Выбери профиль для выбранной записи<select id="v34ProfileSelect"><option value="">— Создать профиль —</option></select></label>'+
 '<label>Новый исполнитель<input id="v34Name" type="text" maxlength="65" placeholder="Сценическое имя или псевдоним"></label>'+
 '<label class="v34-own"><input type="checkbox" id="v34Rights"> Я владею голосом или имею согласие исполнителя</label>'+
 '<div class="v34-row"><button id="v34Create" type="button">Создать профиль</button><button id="v34Attach" type="button">Привязать выбранную запись</button></div>'+
 '<p class="v34-note" id="v34Status"></p>';
 voiceSelect.insertAdjacentElement("afterend",panel);
 const wizardRow=document.createElement("section");wizardRow.className="v34-panel";
 wizardRow.innerHTML='<strong>Чей голос записываем?</strong>'+
 '<label>Выбрать существующего исполнителя<select id="v34WizardProfile"><option value="">— Новый исполнитель —</option></select></label>'+
 '<label>Новый исполнитель (если нет в списке)<input id="v34WizardName" maxlength="65" placeholder="Например, Гость / Артист 2"></label>'+
 '<p class="v34-note">При сохранении запись будет связана с конкретным артистом. Для обучающих датасетов голоса разных людей не объединяются.</p>';
 wizard.append(wizardRow);
 let profiles=[];
 const show=message=>{const el=$("v34Status");if(el)el.textContent=message};
 async function request(endpoint,body){
  const response=await fetch(endpoint,{method:"POST",headers:{"Content-Type":"application/json"},
    body:JSON.stringify(body)});
  const result=await response.json();
  if(!response.ok)throw Error(result.error||"HTTP "+response.status);
  return result;
 }
 function render(){
  for(const id of ["v34ProfileSelect","v34WizardProfile"]){
   const box=$(id);const old=box.value;box.replaceChildren();
   const empty=document.createElement("option");empty.value="";empty.textContent=id==="v34WizardProfile"?"— Новый исполнитель —":"— Не выбран —";
   box.appendChild(empty);
   for(const profile of profiles){
     const opt=document.createElement("option");opt.value=profile.id;opt.textContent=profile.name+" · "+profile.id.slice(-5);
     box.append(opt);
   }
   if([...box.options].some(x=>x.value===old))box.value=old;
  }
 }
 async function reload(){
  const response=await fetch("/api/voice-profiles",{cache:"no-store"});
  if(!response.ok)throw Error("Cannot read artist profiles");
  const data=await response.json();profiles=Array.isArray(data.profiles)?data.profiles:[];
  render();
  show("Профилей: "+profiles.length+". Не назначено голосовых записей: "+data.unassigned_recordings);
 }
 async function create(name,language="ru"){
  name=String(name||"").trim();
  if(name.length<2)throw Error("Укажи имя исполнителя (не менее 2 символов)");
  const response=await request("/api/voice-profiles/create",{name,language,permission:true});
  await reload();return response.profile;
 }
 $("v34Create").addEventListener("click",async()=>{
  if(!$("v34Rights").checked)return show("Подтверди право использовать голос");
  try{
   const profile=await create($("v34Name").value);
   $("v34ProfileSelect").value=profile.id;
   show("Профиль «"+profile.name+"» создан. Теперь привяжи к нему запись.");
  }catch(err){show("Ошибка: "+err.message)}
 });
 $("v34Attach").addEventListener("click",async()=>{
  const file=voiceSelect.value,profile_id=$("v34ProfileSelect").value;
  if(!file||!profile_id)return show("Сначала выбери запись и профиль");
  if(!$("v34Rights").checked)return show("Подтверди право использовать голос");
  try{
   await request("/api/voice-profiles/assign",{voice:file,profile_id,permission:true});
   show("Запись привязана к исполнителю; смешивание профилей заблокировано.");
   document.dispatchEvent(new Event("studioProfiles34:updated"));
  }catch(err){show("Ошибка: "+err.message)}
 });
 async function bindUploadedVoice(filename){
  if(!$("voiceOwn").checked)throw Error("Для записи обязательно разрешение исполнителя");
  const selected=$("v34WizardProfile").value;
  let profile_id=selected;
  if(!profile_id){
   const name=$("v34WizardName").value.trim();
   if(!name)return {assigned:false,reason:"Имя исполнителя не задано; запись пока без профиля"};
   const profile=await create(name,$("voiceLang").value);
   profile_id=profile.id;
  }
  await request("/api/voice-profiles/assign",{voice:filename,profile_id,permission:true});
  document.dispatchEvent(new Event("studioProfiles34:updated"));
  return {assigned:true,profile_id};
 }
 window.studioProfiles34={bindUploadedVoice,refresh:reload};
 reload().catch(err=>show(err.message));
});
