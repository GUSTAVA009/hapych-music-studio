"""Regression for Music Studio HTTP reachability and ACE-Step launch profiles.
Runs with locally installed ACE-Step Python environment; no models load,
no music generation, no user songs modified. Socket bound to 127.0.0.1 only.
"""
from pathlib import Path
import os,sys,threading,unittest
from unittest import mock
import requests
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/"app"))
os.environ["MUSIC_STUDIO_DISABLE_ENGINE_AUTOSTART"]="1"
import studio_server as app

class FakeEngineProcess:
    pid=99
    def poll(self):return None

class TestMusicStudioHTTP(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),app.Handler)
        cls.server.daemon_threads=True
        cls.port=cls.server.server_port
        cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.session=requests.Session()
        cls.session.trust_env=False
        cls.url="http://127.0.0.1:"+str(cls.port)
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=5)
        cls.session.close()
    def test_01_health_works_while_ace_engine_missing(self):
        with mock.patch.object(app,"engine_ok",return_value=False), \
             mock.patch.object(app.training_reservation23,"status",return_value={"active":False}), \
             mock.patch.object(app.training41_guard,"status",return_value={"active":False}), \
             mock.patch.object(app.training32_guard,"status",return_value={"active":False}), \
             mock.patch.object(app.workflow,"lyrics_active",return_value=False):
            r=self.session.get(self.url+"/api/health",timeout=8)
        self.assertEqual(r.status_code,200,r.text[:300])
        value=r.json()
        self.assertTrue(value["server_ready"])
        self.assertFalse(value["ready"])
        self.assertIn(value["engine"]["status"],("not_started","missing","error","starting"))
        self.assertNotIn("RTX 4060",str(value))
        self.assertIn("groove_reference", value)
        self.assertIn("available", value["groove_reference"])
        self.assertNotIn("C:\\Users\\", str(value["groove_reference"]))
        self.assertTrue(value["groove_reference"]["optional"])
    def test_02_prepare_unhandled_exception_is_http_json_not_failed_fetch(self):
        payload={"style":"ambient","lyrics":"[Instrumental]","instrumental":True}
        with mock.patch.object(app,"prepare_request",side_effect=RuntimeError("simulated preflight failure")), \
             mock.patch.object(app.training_reservation23,"status",return_value={"active":False}), \
             mock.patch.object(app.training41_guard,"status",return_value={"active":False}):
            r=self.session.post(self.url+"/api/prepare",json=payload,timeout=12)
        self.assertEqual(r.status_code,500,r.text[:300])
        obj=r.json()
        self.assertEqual(obj["error_type"],"RuntimeError")
        self.assertIn("Diagnose-Windows.ps1",obj["error"])
        self.assertRegex(obj["error_id"],r"^[0-9a-f]{10}$")
    def test_03_health_unhandled_exception_is_http_json(self):
        with mock.patch.object(app,"engine_ok",return_value=False), \
             mock.patch.object(app.training_reservation23,"status",side_effect=KeyError("simulated missing metadata")):
            r=self.session.get(self.url+"/api/health",timeout=12)
        self.assertEqual(r.status_code,500)
        self.assertEqual(r.json()["error_type"],"KeyError")
    def test_04_preparation_does_not_launch_gpu(self):
        payload={"style":"ambient","lyrics":"[Instrumental]","instrumental":True}
        with mock.patch.object(app,"prepare_request",return_value={
                    "caption":"Ambient instrumental","lyrics":"[Instrumental]",
                    "warnings":[]}), \
             mock.patch.object(app.training_reservation23,"status",return_value={"active":False}), \
             mock.patch.object(app.training41_guard,"status",return_value={"active":False}):
            r=self.session.post(self.url+"/api/prepare",json=payload,timeout=12)
        self.assertEqual(r.status_code,200,r.text[:250])
        self.assertEqual(r.json()["caption"],"Ambient instrumental")
    def test_05_diagnostics_is_local_and_does_not_include_user_media(self):
        with mock.patch.object(app,"engine_ok",return_value=False):
            r=self.session.get(self.url+"/api/diagnostics",timeout=12)
        self.assertEqual(r.status_code,200)
        self.assertTrue(r.json()["local_server"])
        self.assertNotIn("Мои треки",r.text)
    def test_06_hardware_flags_use_auto_and_only_one_engine(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory(prefix="hapych-pc-profile-") as tmp:
            folder=Path(tmp)
            executable=folder/".venv"/"Scripts"/"acestep.exe"
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b"mock executable")
            logfile=folder/"Music Studio.log"
            oldproc,olderr=app._engine_process,app._engine_start_error
            try:
                app._engine_process=None
                app._engine_start_error=""
                with mock.patch.object(app,"ENGINE",folder), \
                     mock.patch.object(app,"LOG",logfile), \
                     mock.patch.object(app,"engine_ok",return_value=False), \
                     mock.patch.object(app.subprocess,"Popen",return_value=FakeEngineProcess()) as pop:
                    app.start_engine()
                    app.start_engine()  # must not spawn two engines during slow download
                    self.assertEqual(pop.call_count,1)
                    args=pop.call_args.args[0]
                    self.assertNotIn("--lm_model_path",args)
                    self.assertNotIn("--init_llm",args)
                    self.assertNotIn("--quantization",args)
                    self.assertNotIn("--offload_to_cpu",args)
                    self.assertNotIn("--offload_dit_to_cpu",args)
                    env=pop.call_args.kwargs["env"]
                    if "CUDA_VISIBLE_DEVICES" not in os.environ:
                        self.assertNotIn("CUDA_VISIBLE_DEVICES",env)
            finally:
                app._engine_process=oldproc
                app._engine_start_error=olderr

if __name__=="__main__":
    unittest.main(verbosity=2)
