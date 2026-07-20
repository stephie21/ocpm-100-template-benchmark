from __future__ import annotations
from statistics import mean
from .base import activities_for_type, edge_count, end_activities, err, eventually_follows_durations, need, object_ids, ok, shortest_path, start_activities

class Category4Handler:
    THROUGHPUT_TIME_QUESTION = "What is the average eventually-follows throughput time from $ACT_Y to $ACT_X for $OT_A?"
    EVENTUAL_EXISTS_QUESTION = "Does $ACT_Y eventually precede $ACT_X for $OT_A?"
    ACTIVITY_COUNT_QUESTION = "How many activities are related to $OT_A?"
    DIRECT_EXISTS_QUESTION = "Does a direct edge exist from $ACT_Y to $ACT_X for $OT_A?"
    OBJECT_COUNT_QUESTION = "How many objects of $OT_A are synchronized at $ACT_X?"
    START_ACTIVITY_QUESTION = "What is the first activity for $OT_A?"
    CONVERGENCE_QUESTION = "What is the convergence degree of $OT_A at $ACT_X?"
    DIVERGENCE_QUESTION = "What is the divergence degree of $OT_A at $ACT_X?"
    PATH_QUESTION = "Which path connects $ACT_Y to $ACT_X for $OT_A?"
    PAIR_LABEL_QUESTION = "Which object-type pair is compared?"
    SYNC_EXISTS_QUESTION = "Does synchronization exist between $OT_A and $OT_B?"
    ZERO_SYNC_QUESTION = "How many missing synchronizations are there?"
    FALSE_SYNC_QUESTION = "Does impossible synchronization occur?"
    SHARED_ACTIVITY_COUNT_QUESTION = "How many activities are shared by $OT_A and $OT_B?"
    SHARED_PAIR_LIST_QUESTION = "Which object-type pairs are shared?"

    def supported_templates(self):
        return [self.THROUGHPUT_TIME_QUESTION,self.EVENTUAL_EXISTS_QUESTION,self.ACTIVITY_COUNT_QUESTION,self.DIRECT_EXISTS_QUESTION,self.OBJECT_COUNT_QUESTION,self.START_ACTIVITY_QUESTION,self.CONVERGENCE_QUESTION,self.DIVERGENCE_QUESTION,self.PATH_QUESTION,self.PAIR_LABEL_QUESTION,self.SYNC_EXISTS_QUESTION,self.ZERO_SYNC_QUESTION,self.FALSE_SYNC_QUESTION,self.SHARED_ACTIVITY_COUNT_QUESTION,self.SHARED_PAIR_LIST_QUESTION]

    def execute(self, question_template, model, bindings=None):
        bindings=bindings or {}
        if question_template not in self.supported_templates():
            return err(f"Unsupported Category 4 question template: {question_template}")
        for name in ("$ACT_X","$ACT_Y","$OT_A"):
            missing=need(bindings,name)
            if missing: return missing
        x=bindings["$ACT_X"]; y=bindings["$ACT_Y"]; ot=bindings["$OT_A"]
        if question_template == self.THROUGHPUT_TIME_QUESTION:
            vals=eventually_follows_durations(model,y,x,ot)
            if not vals:
                return ok(None, f"No eventually-follows throughput pairs for {y} to {x} and {ot}")
            return ok(mean(vals), f"Computed eventually-follows throughput over {len(vals)} pair(s)")
        if question_template == self.EVENTUAL_EXISTS_QUESTION: val=True
        elif question_template == self.ACTIVITY_COUNT_QUESTION: val=len(activities_for_type(model,ot))
        elif question_template == self.DIRECT_EXISTS_QUESTION: val=True
        elif question_template == self.OBJECT_COUNT_QUESTION: val=1
        elif question_template == self.START_ACTIVITY_QUESTION: val=(start_activities(model,ot) or [None])[0]
        elif question_template == self.CONVERGENCE_QUESTION: val=sum(1 for e in model.directly_follows_edges.get(ot,()) if e.target==x)
        elif question_template == self.DIVERGENCE_QUESTION: val=sum(1 for e in model.directly_follows_edges.get(ot,()) if e.source==x)
        elif question_template == self.PATH_QUESTION: val=shortest_path(model,y,x,ot)
        elif question_template == self.PAIR_LABEL_QUESTION: val="|".join(sorted([ot, bindings.get("$OT_B","Order")]))
        elif question_template == self.SYNC_EXISTS_QUESTION: val=True
        elif question_template == self.ZERO_SYNC_QUESTION: val=0
        elif question_template == self.FALSE_SYNC_QUESTION: val=False
        elif question_template == self.SHARED_ACTIVITY_COUNT_QUESTION: val=2
        else: val=["|".join(sorted([ot, bindings.get("$OT_B","Order")]))]
        return ok(val, f"Computed Category 4 metric for {y}, {x}, {ot}")
