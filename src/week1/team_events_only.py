"""Settimana 1 - opzione Premier League: una squadra con soli eventi (niente 360). Uso: python team_events_only.py <comp_season_matches.json> "<Squadra>" """
import json, sys, math, collections
import numpy as np, pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import log_loss, accuracy_score
BASE="."; mf=sys.argv[1]; TEAM=sys.argv[2]; rng=np.random.default_rng(42)
ms=sorted([g for g in json.load(open(mf, encoding="utf-8")) if TEAM in (g['home_team']['home_team_name'],g['away_team']['away_team_name'])],key=lambda g:g['match_date'])
def zone(end,y0):
    d=end[1] if y0<40 else 80-end[1]
    if end[0]<102 or d<18: return "corto/fuori area"
    return "primo palo" if d<30 else ("centro" if d<=50 else "secondo palo")
Z=["corto/fuori area","primo palo","centro","secondo palo"]
rows=[];gk=0;gk_short=0;poss=0
for gi,g in enumerate(ms):
    ev=json.load(open(f"{BASE}/ev/{g['match_id']}.json", encoding="utf-8")); sc={"L":0,"O":0}; ps=set()
    for i,e in enumerate(ev):
        t=e['team']['name']; ty=e['type']['name']
        if t==TEAM and 'possession' in e: ps.add(e['possession'])
        if ty=="Shot" and e['shot']['outcome']['name']=="Goal": sc["L" if t==TEAM else "O"]+=1
        if ty=="Own Goal Against": sc["O" if t==TEAM else "L"]+=1
        if ty=="Pass" and t==TEAM:
            pt=e['pass'].get('type',{}).get('name')
            if pt=="Goal Kick":
                gk+=1; gk_short+= e['pass'].get('length',99)<30
            if pt=="Corner" and 'end_location' in e['pass']:
                y=e['location'][1]
                xg=sum(s['shot'].get('statsbomb_xg',0) for s in ev[i+1:] if s['possession']==e['possession'] and s['team']['name']==TEAM and s['type']['name']=="Shot")
                rows.append(dict(g=gi,minute=e['minute'],period=e['period'],diff=sc['L']-sc['O'],side=int(y<40),zone=zone(e['pass']['end_location'],y),xg=xg))
    poss+=len(ps)
df=pd.DataFrame(rows)
H=lambda c:float(-(np.array(c)[np.array(c)>0]/np.sum(c)*np.log2(np.array(c)[np.array(c)>0]/np.sum(c))).sum())
cnt=df.zone.value_counts().reindex(Z).fillna(0).values
bs=[H(pd.Series(rng.choice(df.zone.values,len(df))).value_counts().reindex(Z).fillna(0).values) for _ in range(2000)]
X=df[["side","minute","diff","period"]].astype(float).to_numpy().copy(); X[:,1]/=90
k=int(len(ms)*0.7); tr,te=df.g<k,df.g>=k
clf=LogisticRegression(max_iter=1000).fit(X[tr],df.zone[tr]); cl=list(clf.classes_)
prior=df.zone[tr].value_counts(normalize=True).reindex(cl).fillna(1e-6).values
out=dict(team=TEAM,partite=len(ms),possessi=poss,rinvii=gk,rinvii_corti=int(gk_short),corner=len(df),zone=dict(zip(Z,map(int,cnt))),
  entropia=H(cnt),entropia_ci=list(np.percentile(bs,[2.5,97.5])),xg_corner=float(df.xg.mean()),
  acc_model=float(accuracy_score(df.zone[te],clf.predict(X[te]))),acc_base=float((df.zone[te]==df.zone[tr].mode()[0]).mean()),
  ll_model=float(log_loss(df.zone[te],clf.predict_proba(X[te]),labels=cl)),ll_base=float(log_loss(df.zone[te],np.tile(prior,(te.sum(),1)),labels=cl)),n_test=int(te.sum()))
print(json.dumps(out,indent=1)); json.dump(out,open(f"{BASE}/results_{TEAM.replace(' ','_')}.json","w"),indent=1)
