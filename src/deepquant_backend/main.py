import threading
import uuid
from typing import Dict

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .backtest import BacktestRunner
from .policy_parser import LangChainPolicyParser
from .schemas import BacktestRequest, BacktestStatus, PolicyRequest, PolicyResponse
from .store import PolicyStore

# Load environment variables from .env if present
load_dotenv()

app = FastAPI(title="DeepQuant Backtester", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

policy_store = PolicyStore()
parser = LangChainPolicyParser()


class JobRegistry:
    def __init__(self):
        self.jobs: Dict[str, BacktestStatus] = {}
        self.lock = threading.Lock()

    def create(self, job_id: str) -> BacktestStatus:
        status = BacktestStatus(
            job_id=job_id, status="pending", progress=0.0, message="Queued"
        )
        with self.lock:
            self.jobs[job_id] = status
        return status

    def update(self, job_id: str, status: BacktestStatus):
        with self.lock:
            self.jobs[job_id] = status

    def get(self, job_id: str) -> BacktestStatus:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                raise KeyError(job_id)
            return job


job_registry = JobRegistry()


@app.get("/api/health")
def health():
    return {"ok": True}


@app.post("/api/policies", response_model=PolicyResponse)
def create_policy(payload: PolicyRequest):
    parsed = parser.parse(payload.prompt, payload.name)
    policy_id = str(uuid.uuid4())
    policy_store.add_policy(
        policy_id, prompt=payload.prompt, strategy=parsed.strategy, name=parsed.name
    )
    return PolicyResponse(policy_id=policy_id, strategy=parsed.strategy)


@app.get("/api/policies")
def list_policies():
    return policy_store.list_policies()


@app.post("/api/backtests", response_model=BacktestStatus)
def start_backtest(payload: BacktestRequest, background_tasks: BackgroundTasks):
    if not payload.prompt and not payload.policy_id:
        raise HTTPException(
            status_code=400, detail="Provide either a prompt or an existing policy_id"
        )

    job_id = str(uuid.uuid4())
    status = job_registry.create(job_id)
    background_tasks.add_task(run_backtest_job, job_id, payload)
    return status


@app.get("/api/backtests/{job_id}", response_model=BacktestStatus)
def backtest_status(job_id: str):
    try:
        return job_registry.get(job_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Job not found")


def run_backtest_job(job_id: str, payload: BacktestRequest):
    try:
        parsed = None
        policy_id = payload.policy_id
        if payload.prompt:
            parsed = parser.parse(payload.prompt, payload.name)
            policy_id = str(uuid.uuid4())
            policy_store.add_policy(
                policy_id, payload.prompt, parsed.strategy, parsed.name
            )
        elif payload.policy_id:
            policy = policy_store.get_policy(payload.policy_id)
            if not policy:
                raise ValueError("Policy not found")
            parsed = parser.parse(policy.prompt, policy.name)
            policy_id = policy.id
        else:
            raise ValueError("No policy provided")

        def progress_cb(progress: float, message: str):
            job_registry.update(
                job_id,
                BacktestStatus(
                    job_id=job_id,
                    status="running",
                    progress=round(progress, 3),
                    message=message,
                ),
            )

        runner = BacktestRunner(progress_cb=progress_cb)
        result = runner.run(parsed.strategy, policy_id=policy_id)
        job_registry.update(
            job_id,
            BacktestStatus(
                job_id=job_id,
                status="completed",
                progress=1.0,
                message="Done",
                result=result,
            ),
        )
    except Exception as exc:  # noqa: BLE001
        job_registry.update(
            job_id,
            BacktestStatus(
                job_id=job_id,
                status="failed",
                progress=1.0,
                message=str(exc),
                result=None,
            ),
        )
