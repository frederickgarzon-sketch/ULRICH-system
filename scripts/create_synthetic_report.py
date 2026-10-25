"""Create a clearly labelled synthetic report for UI demonstration."""
from __future__ import annotations
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sqlalchemy import select
from app.database.database import SessionLocal, initialize_database
from app.database.models import (AttentionTrial, BlinkEvent, BodyMovementEvent,
    BodyMovementSample, HeadMovementEvent, HeadPoseSample, MonitoringSession,
    Participant, PostureEvent, SessionSummary)

def main() -> int:
    initialize_database(); rng=random.Random(20260918)
    with SessionLocal() as db:
        participant=db.scalar(select(Participant).where(Participant.participant_code=="P-001"))
        if participant is None: raise SystemExit("Participant P-001 was not found.")
        start=datetime.now(timezone.utc)-timedelta(minutes=8)
        session=MonitoringSession(participant_id=participant.id,mode="synthetic",status="completed",
            start_time=start,end_time=start+timedelta(minutes=8),notes=(
            "SYNTHETIC DEMONSTRATION ONLY. This scenario assumes a previously documented ADHD "
            "diagnosis solely to preview the report. The system did not produce a diagnosis."))
        db.add(session);db.flush()
        blink_times=[18,35,51,73,91,108,127,145,166,184,201,219,238,256,279,301,322,344,365,389,411,432,451,469]
        for second in blink_times: db.add(BlinkEvent(session_id=session.id,session_seconds=second,average_ear=round(rng.uniform(.14,.19),3)))
        for second in range(0,481,5):
            db.add(HeadPoseSample(session_id=session.id,session_seconds=second,yaw=round(rng.gauss(0,5.8),2),pitch=round(rng.gauss(0,4.6),2),roll=round(rng.gauss(0,2.3),2)))
            db.add(BodyMovementSample(session_id=session.id,session_seconds=second,magnitude=round(max(0,rng.gauss(.026,.015)),4),regional_json="{}"))
        directions=["LEFT","RIGHT","DOWN","LEFT","UP","RIGHT","LEFT","DOWN","RIGHT","UP","LEFT","RIGHT","DOWN","LEFT"]
        for index,direction in enumerate(directions,1): db.add(HeadMovementEvent(session_id=session.id,session_seconds=index*29,direction=direction,magnitude=round(rng.uniform(13,27),1)))
        for index in range(19): db.add(BodyMovementEvent(session_id=session.id,session_seconds=12+index*24,magnitude=round(rng.uniform(.045,.11),4)))
        for second,angle in ((96,16.2),(207,18.7),(318,15.4),(423,20.1)): db.add(PostureEvent(session_id=session.id,session_seconds=second,posture_angle=angle))
        reaction_times=[510,620,470,None,780,560,690,430,None,850,590,540,730,480,640,None,910,520,610,760,490,680,550,820,460,700,None,580,660,530]
        correct_set={1,2,3,5,6,8,10,11,13,14,17,18,19,21,22,24,25,27,29}
        for number,rt in enumerate(reaction_times,1):
            missed=rt is None;correct=number in correct_set and not missed
            db.add(AttentionTrial(session_id=session.id,trial_number=number,stimulus="target" if number%3==0 else "non_target",is_target=number%3==0,stimulus_session_seconds=number*8,reaction_time_ms=rt,responded=not missed,correct=correct,incorrect=not missed and not correct,missed=missed,false_response=not missed and not correct and number%3!=0))
        db.add(SessionSummary(session_id=session.id,duration_seconds=480,total_blinks=len(blink_times),average_blink_rate=3.0,head_movements=len(directions),body_movement_events=19,posture_changes=4,mock_data=True,summary_json='{"synthetic":true,"purpose":"report_preview"}'))
        db.commit();print(session.id);return session.id

if __name__=="__main__": main()
