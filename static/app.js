const state={lat:null,lon:null,place:'',geo:null,weather:null,battery:null,monitoring:false,places:[]};
const $=s=>document.querySelector(s);
const esc=v=>String(v??'').replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
function toast(msg){const t=$('#toast');t.textContent=msg;t.classList.add('show');clearTimeout(window.toastTimer);window.toastTimer=setTimeout(()=>t.classList.remove('show'),2800)}
function openModal(id='modal'){if(id==='modal')populatePlaceSelect();document.getElementById(id).classList.remove('hidden')}
function openReminderModal(){openModal('modal')}
function openPlaceModal(){openModal('placeModal');if(state.lat!=null)fillSaveLocation()}
function closeModal(id){document.getElementById(id).classList.add('hidden')}
function switchView(view){document.querySelectorAll('.view').forEach(x=>x.classList.add('hidden-view'));$('#view-'+view).classList.remove('hidden-view');document.querySelectorAll('.nav[data-view]').forEach(x=>x.classList.toggle('active',x.dataset.view===view));if(view==='places')loadPlaces();if(view==='reminders')loadReminders();if(view==='activity')loadLogs()}
document.querySelectorAll('.nav[data-view]').forEach(b=>b.onclick=()=>switchView(b.dataset.view));

async function getLocation(){
 if(!navigator.geolocation){toast('This browser does not support GPS location.');return}
 toast('Requesting your current location…');
 navigator.geolocation.getCurrentPosition(async p=>{
   state.lat=p.coords.latitude;state.lon=p.coords.longitude;
   $('#coords').textContent=`${state.lat.toFixed(5)}, ${state.lon.toFixed(5)} · ±${Math.round(p.coords.accuracy||0)}m`;
   $('#latInput').value=state.lat;$('#lonInput').value=state.lon;
   $('#saveLat').value=state.lat;$('#saveLon').value=state.lon;
   await Promise.all([reverseGeocode(),loadWeather()]);
   state.monitoring=true;$('#monitorStatus').textContent='Live context monitoring';
   toast('✓ Location, place and weather updated');
   checkContext();
 },e=>{toast(e.code===1?'Location permission was denied. Enable it in browser settings.':'Unable to get GPS location.');$('#monitorStatus').textContent='Location permission needed'},{enableHighAccuracy:true,timeout:15000,maximumAge:15000});
}
async function reverseGeocode(){try{const r=await fetch(`/api/reverse-geocode?lat=${state.lat}&lon=${state.lon}`);if(!r.ok)throw Error();const d=await r.json();state.place=d.place;state.geo=d;$('#place').textContent=d.place;$('#placeInput')?.setAttribute('value',d.place);$('#savePlaceName').value=d.place;$('#savePlaceSummary').textContent=[d.village,d.city,d.district,d.state].filter(Boolean).join(' · ');$('#place').title=d.display_name||d.place}catch(e){$('#place').textContent='Location detected'}}
async function loadWeather(){try{const r=await fetch(`/api/weather?lat=${state.lat}&lon=${state.lon}`);if(!r.ok)throw Error();const d=await r.json();state.weather=d.condition;$('#weather').textContent=`${Math.round(d.temperature)}°C · ${d.condition}`;$('#weatherMeta').textContent=`${d.humidity}% humidity · ${d.rain_probability}% rain next hours`}catch(e){state.weather=null;$('#weather').textContent='Weather unavailable';$('#weatherMeta').textContent='Automatic weather service unavailable'}}
async function getBattery(){if(navigator.getBattery){try{const b=await navigator.getBattery();state.battery=Math.round(b.level*100);renderBattery();b.addEventListener('levelchange',()=>{state.battery=Math.round(b.level*100);renderBattery();checkContext()});return}catch(e){}}state.battery=null;$('#battery').textContent='Unavailable';$('#batteryMeta').textContent='Browser does not expose battery status'}
function renderBattery(){if(state.battery!=null){$('#battery').textContent=`${state.battery}%`;$('#batteryMeta').textContent=state.battery<=20?'Low battery · automatic':'Device status · automatic'}}

async function loadPlaces(){try{const r=await fetch('/api/places');state.places=await r.json();renderPlaces();populatePlaceSelect()}catch(e){toast('Could not load saved places')}}
function renderPlaces(){const box=$('#placesList');if(!state.places.length){box.innerHTML='<div class="empty place-empty"><div class="big-icon">⌖</div><b>No saved places yet</b><span>Save your current GPS location or search for a city, village, shop or landmark.</span><button class="primary" onclick="openPlaceModal()">＋ Save Place</button></div>';return}box.innerHTML=state.places.map(p=>`<article class="place-card"><div class="place-icon">⌖</div><div class="place-main"><b>${esc(p.place_name)}</b><span>${esc(p.place_type||'Saved place')}</span><small>${esc([p.village,p.city,p.district,p.state].filter(Boolean).join(' · ')||p.country||'Location')}</small><code>${Number(p.latitude).toFixed(5)}, ${Number(p.longitude).toFixed(5)}</code></div><div class="place-actions"><button class="secondary use-place" onclick="usePlace(${p.id})">Use in reminder</button><button class="delete" onclick="removePlace(${p.id})">×</button></div></article>`).join('')}
function populatePlaceSelect(){const s=$('#reminderPlaceSelect');if(!s)return;const old=s.value;s.innerHTML='<option value="">Use current location</option>'+state.places.map(p=>`<option value="${p.id}">${esc(p.place_name)} · ${esc(p.city||p.village||p.state||'')}</option>`).join('');if(state.places.some(p=>String(p.id)===old))s.value=old}
$('#reminderPlaceSelect').onchange=()=>{const p=state.places.find(x=>String(x.id)===$('#reminderPlaceSelect').value);if(p){$('#latInput').value=p.latitude;$('#lonInput').value=p.longitude;$('#selectedPlacePreview').textContent=`⌖ ${p.place_name} · ${[p.village,p.city,p.district,p.state].filter(Boolean).join(' · ')}`;}else{$('#selectedPlacePreview').textContent=state.lat!=null?`⌖ ${state.place||'Current location'} · ${state.lat.toFixed(5)}, ${state.lon.toFixed(5)}`:'No saved place selected. Your current GPS location will be used.'}}
function usePlace(id){const p=state.places.find(x=>x.id===id);if(!p)return;switchView('reminders');openReminderModal();setTimeout(()=>{$('#reminderPlaceSelect').value=p.id;$('#reminderPlaceSelect').dispatchEvent(new Event('change'))},0)}
async function removePlace(id){if(!confirm('Delete this saved place? Existing reminders keep their coordinates.'))return;const r=await fetch(`/api/places/${id}`,{method:'DELETE'});if(r.ok){toast('Place deleted');loadPlaces()}else toast('Could not delete place')}

async function searchPlaces(){const q=$('#placeSearch').value.trim();if(q.length<2){toast('Type at least 2 characters');return}const box=$('#searchResults');box.innerHTML='<div class="searching">Searching OpenStreetMap…</div>';try{const r=await fetch(`/api/geocode?q=${encodeURIComponent(q)}`);const data=await r.json();if(!data.length){box.innerHTML='<div class="empty">No matching places found.</div>';return}box.innerHTML=data.map((p,i)=>`<button class="result-card" onclick="selectSearchResult(${i})"><span>⌖</span><div><b>${esc(p.place)}</b><small>${esc(p.display_name)}</small></div></button>`).join('');window.searchData=data}catch(e){box.innerHTML='<div class="empty">Place search is temporarily unavailable.</div>'}}
function selectSearchResult(i){const p=window.searchData[i];if(!p)return;openPlaceModal();$('#savePlaceName').value=p.place;$('#saveLat').value=p.latitude;$('#saveLon').value=p.longitude;$('#placeModal select').value=p.city?'City / Town':(p.village?'Village':'Shop / Store');$('#savePlaceSummary').textContent=[p.village,p.city,p.district,p.state].filter(Boolean).join(' · ');window.selectedSearchPlace=p;$('#searchResults').innerHTML=''}
$('#searchPlaceBtn').onclick=searchPlaces;$('#placeSearch').addEventListener('keydown',e=>{if(e.key==='Enter')searchPlaces()});
function fillSaveLocation(){if(state.lat==null)return;$('#savePlaceName').value=state.place||'My current location';$('#saveLat').value=state.lat;$('#saveLon').value=state.lon;$('#savePlaceSummary').textContent=state.geo?[state.geo.village,state.geo.city,state.geo.district,state.geo.state].filter(Boolean).join(' · '):`${state.lat.toFixed(5)}, ${state.lon.toFixed(5)}`}
$('#saveCurrentPlaceBtn').onclick=()=>{if(state.lat==null){getLocation();toast('Getting your location first…');return}openPlaceModal();fillSaveLocation()};$('#saveModalCurrent').onclick=()=>{if(state.lat==null)getLocation();else fillSaveLocation()};$('#useCurrent').onclick=()=>{if(state.lat==null){getLocation();toast('Getting GPS location…');return}$('#reminderPlaceSelect').value='';$('#latInput').value=state.lat;$('#lonInput').value=state.lon;$('#selectedPlacePreview').textContent=`⌖ ${state.place||'Current location'} · ${state.lat.toFixed(5)}, ${state.lon.toFixed(5)}`;toast('Using current location')};

async function loadReminders(){const r=await fetch('/api/reminders');const list=await r.json();renderReminderList($('#reminderList'),list);renderReminderList($('#dashboardReminderList'),list.slice(0,5))}
function renderReminderList(box,list){if(!box)return;if(!list.length){box.innerHTML='<div class="empty">No reminders yet. Create your first context-aware reminder.</div>';return}box.innerHTML=list.map(x=>`<article class="reminder"><div class="card-icon">✦</div><div class="task"><b>${esc(x.task_name)}</b><small>⌖ ${esc(x.place_name)} · radius ${Math.round(x.radius_m)}m</small></div><div class="chips">${x.weather_condition?`<span class="chip">☁ ${esc(x.weather_condition)}</span>`:'<span class="chip">☁ Any weather</span>'}${x.battery_threshold!=null?`<span class="chip">▰ ≤${x.battery_threshold}%</span>`:''}${x.time_start?`<span class="chip">◷ ${x.time_start}–${x.time_end||'?'}</span>`:''}</div><div class="distance" id="dist-${x.id}">—</div><button class="delete" onclick="removeReminder(${x.id})">×</button></article>`).join('')}
async function removeReminder(id){if(!confirm('Delete this reminder?'))return;const r=await fetch(`/api/reminders/${id}`,{method:'DELETE'});if(r.ok){toast('Reminder removed');loadReminders()}else toast('Could not remove reminder')}

async function checkContext(){
  if(state.lat==null) return;
  try{
    const r = await fetch('/api/context', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({latitude: state.lat, longitude: state.lon, weather: state.weather, battery: state.battery})});
    const d = await r.json();
    d.results.forEach(x=>{
      document.querySelectorAll(`#dist-${x.id}`).forEach(el=> el.textContent = x.distance_m < 1000 ? `${Math.round(x.distance_m)}m away` : `${(x.distance_m/1000).toFixed(1)}km`);
      // If server signals a new trigger, show up to `alert_count` notifications (1 for <=1km, 2 for <=200m)
      const count = x.alert_count || 0;
      if(count > 0 && x.new_trigger){
        toast('🔔 '+x.message + (count>1?` (x${count})`:''));
        // Send desktop notifications `count` times with a small interval to make them noticeable
        for(let i=0;i<count;i++){setTimeout(()=>notify(x.message), i*350)}
      }
    });
    loadLogs();
  }catch(e){console.error(e)}
}
async function notify(message){if(!('Notification'in window))return;if(Notification.permission==='default')await Notification.requestPermission();if(Notification.permission==='granted')new Notification('SmartRemind',{body:message})}
async function loadLogs(){try{const r=await fetch('/api/logs');const list=await r.json();$('#logs').innerHTML=list.length?list.map(x=>`<div class="log"><b>🔔 ${esc(x.task_name)}</b><span>${esc(x.message)} · ${new Date(x.created_at).toLocaleString()}</span></div>`).join(''):'<div class="empty">No context events yet.</div>'}catch(e){}}

$('#form').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);const data=Object.fromEntries(f.entries());delete data.place_id;['latitude','longitude','radius_m'].forEach(k=>data[k]=Number(data[k]));const selected=state.places.find(p=>String(p.id)===$('#reminderPlaceSelect').value);if(selected)data.place_name=selected.place_name;else data.place_name=state.place||'Current location';if(data.battery_threshold==='')data.battery_threshold=null;if(data.weather_condition==='')data.weather_condition=null;for(const k of ['time_start','time_end'])if(!data[k])data[k]=null;try{const r=await fetch('/api/reminders',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok)throw Error();e.target.reset();$('#selectedPlacePreview').textContent='No saved place selected. Your current GPS location will be used.';closeModal('modal');toast('✓ Smart reminder created');loadReminders()}catch(err){toast('Could not create reminder')}};
$('#placeForm').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target);const data=Object.fromEntries(f.entries());['latitude','longitude'].forEach(k=>data[k]=Number(data[k]));if(window.selectedSearchPlace){Object.assign(data,window.selectedSearchPlace);data.place_name=$('#savePlaceName').value;data.place_type=f.get('place_type')}try{const r=await fetch('/api/places',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!r.ok)throw Error();closeModal('placeModal');e.target.reset();window.selectedSearchPlace=null;toast('✓ Place saved successfully');await loadPlaces();switchView('places')}catch(err){toast('Could not save place')}};
$('#locBtn').onclick=getLocation;$('#themeBtn').onclick=()=>{document.body.classList.toggle('dark');localStorage.dark=document.body.classList.contains('dark')?'1':'0'};if(localStorage.dark==='1')document.body.classList.add('dark');
window.addEventListener('click',e=>{if(e.target.classList.contains('modal'))e.target.classList.add('hidden')});
getLocation();getBattery();loadPlaces();loadReminders();loadLogs();setInterval(()=>{if(state.lat!=null){loadWeather();checkContext()}},30000);setInterval(()=>{if(state.lat!=null)checkContext()},5000);
