"use strict";
/* Lossless microphone capture for Music Studio, Chromium AudioWorklet.
   No cloud transmission; no compressor/AGC/noise gate. MediaRecorder remains
   the fallback in workflow.js. The listener decides when to save the file. */
(function(){
  const workletSource=[
    "class StudioPCMProcessor extends AudioWorkletProcessor {",
    " constructor(){super();this.buf=new Float32Array(4096);this.i=0;this.port.onmessage=e=>{if(e.data&&e.data.type==='flush'){this.flush();this.port.postMessage({type:'end'});}};}",
    " flush(){if(this.i){const x=this.buf.slice(0,this.i);this.i=0;this.port.postMessage({type:'samples',value:x.buffer},[x.buffer]);}}",
    " process(inputs){const a=inputs[0]&&inputs[0][0];if(a){for(let i=0;i<a.length;i++){this.buf[this.i++]=a[i];if(this.i===this.buf.length)this.flush();}}return true;}",
    "}",
    "registerProcessor('studio-pcm-recorder',StudioPCMProcessor);"
  ].join("\n");
  class StudioLosslessRecorder extends EventTarget {
    constructor(stream) {
      super();
      this.stream=stream;
      this.state="inactive";
      this.mimeType="audio/wav";
      this.samples=[];
      this.sampleRate=48000;
      this.pendingStop=false;
      this.completed=false;
      this.context=null;
      this.node=null;
      this.source=null;
      this.silent=null;
    }
    static encodeWAV(chunks,rate) {
      let count=0;
      for(const chunk of chunks) count+=chunk.length;
      if(count<100) throw new Error("Не записан звуковой сигнал.");
      const bytes=44+count*2;
      if(bytes>19*1024*1024) throw new Error("Запись WAV превышает допустимый размер.");
      const buf=new ArrayBuffer(bytes);
      const view=new DataView(buf);
      const fourcc=(offset,s)=>{for(let i=0;i<s.length;i++)view.setUint8(offset+i,s.charCodeAt(i));};
      fourcc(0,"RIFF");view.setUint32(4,bytes-8,true);fourcc(8,"WAVE");
      fourcc(12,"fmt ");view.setUint32(16,16,true);view.setUint16(20,1,true);
      view.setUint16(22,1,true);view.setUint32(24,rate,true);
      view.setUint32(28,rate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);
      fourcc(36,"data");view.setUint32(40,count*2,true);
      let off=44;
      for(const chunk of chunks) {
        for(let j=0;j<chunk.length;j++) {
          const x=Math.max(-1,Math.min(1,chunk[j]));
          view.setInt16(off,x<0?Math.round(x*32768):Math.round(x*32767),true);
          off+=2;
        }
      }
      return new Blob([buf],{type:"audio/wav"});
    }
    start() {
      if(this.state!=="inactive") throw new Error("Запись уже идёт.");
      this.state="recording";
      this.pendingStop=false;
      this.completed=false;
      this._begin().catch(error=>this._failed(error));
    }
    async _begin() {
      const AudioCtx=window.AudioContext||window.webkitAudioContext;
      this.context=new AudioCtx({sampleRate:48000});
      if(!this.context.audioWorklet) throw new Error("AudioWorklet не поддерживается.");
      this.sampleRate=this.context.sampleRate;
      const moduleURL=URL.createObjectURL(new Blob([workletSource],{type:"application/javascript"}));
      try {await this.context.audioWorklet.addModule(moduleURL);}
      finally {URL.revokeObjectURL(moduleURL);}
      this.node=new AudioWorkletNode(this.context,"studio-pcm-recorder",{
        numberOfInputs:1,numberOfOutputs:1,outputChannelCount:[1]
      });
      this.node.port.onmessage=event=>{
        const message=event.data||{};
        if(message.type==="samples") {
          this.samples.push(new Float32Array(message.value));
        } else if(message.type==="end") {
          this._finalize();
        }
      };
      this.source=this.context.createMediaStreamSource(this.stream);
      this.silent=this.context.createGain();
      this.silent.gain.value=0;
      this.source.connect(this.node);
      this.node.connect(this.silent);
      this.silent.connect(this.context.destination);
      await this.context.resume();
      if(this.pendingStop)this.node.port.postMessage({type:"flush"});
    }
    stop() {
      if(this.state!=="recording") return;
      this.state="inactive";
      this.pendingStop=true;
      if(this.node)this.node.port.postMessage({type:"flush"});
    }
    _notify(eventName,extra) {
      const event=new Event(eventName);
      if(extra)Object.assign(event,extra);
      this.dispatchEvent(event);
    }
    _failed(error) {
      if(this.completed) return;
      this.completed=true;
      this.state="inactive";
      this._cleanup();
      this._notify("error",{error});
    }
    _finalize() {
      if(this.completed) return;
      this.completed=true;
      try {
        const blob=StudioLosslessRecorder.encodeWAV(this.samples,this.sampleRate);
        this._notify("dataavailable",{data:blob});
        this._notify("stop");
      } catch(error) {
        this._notify("error",{error});
      } finally {
        this._cleanup();
      }
    }
    _cleanup() {
      try{this.source&&this.source.disconnect();}catch(_){}
      try{this.node&&this.node.disconnect();}catch(_){}
      try{this.silent&&this.silent.disconnect();}catch(_){}
      try{this.node&&this.node.port.close();}catch(_){}
      if(this.context) this.context.close().catch(()=>{});
      this.samples=[];
    }
  }
  window.StudioLosslessRecorder=StudioLosslessRecorder;
})();