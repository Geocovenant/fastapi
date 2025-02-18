from sqlmodel import Session, select
from api.public.poll.models import Poll, PollOption

def get_all_polls(db: Session):
    query = select(Poll, PollOption).join(PollOption)
    results = db.exec(query).all()
    
    polls_dict = {}
    for poll, option in results:
        if poll.id not in polls_dict:
            polls_dict[poll.id] = poll.dict()
            polls_dict[poll.id]['options'] = []
        polls_dict[poll.id]['options'].append(option.dict())
    
    return list(polls_dict.values())