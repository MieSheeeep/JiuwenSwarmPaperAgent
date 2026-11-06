"""Pure document-only ranking and answer scoring for QA plugins."""
from collections import Counter
import math
import re
import statistics
import string


def normalize(text):
    text=''.join(c for c in str(text).lower() if c not in string.punctuation)
    return ' '.join(re.sub(r'\b(a|an|the)\b',' ',text).split())


def score(pred,gold):
    p,g=normalize(pred),normalize(gold);em=float(p==g)
    if p in ('yes','no','noanswer') or g in ('yes','no','noanswer'):return em,em
    common=sum((Counter(p.split())&Counter(g.split())).values())
    return em,2*common/(len(p.split())+len(g.split())) if common else 0.


def rank(question,passages):
    tokens=lambda s:re.findall('[a-z0-9]+',s.lower())
    query=set(tokens(question))-set('a an the of in on to and or is was were are which what who did'.split())
    docs=[tokens(p['title']+' '+p['text']) for p in passages]
    avg=max(1,statistics.mean(map(len,docs)))
    df=Counter(t for d in docs for t in set(d));values=[]
    for i,doc in enumerate(docs):
        counts=Counter(doc)
        value=sum(math.log(1+(len(docs)-df[t]+.5)/(df[t]+.5))*counts[t]*2.2 /
            (counts[t]+1.2*(.25+.75*len(doc)/avg)) for t in query if counts[t])
        values.append((value,i))
    return [passages[i] for _,i in sorted(values,key=lambda x:(-x[0],x[1]))]
