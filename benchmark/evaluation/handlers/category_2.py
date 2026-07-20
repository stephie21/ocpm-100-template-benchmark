from __future__ import annotations
from statistics import mean
from .base import count_activity_for_type, edge_count, edge_durations, err, need, ok, unique_objects_for_activity

class Category2Handler:
    ACTIVITY_EVENTS_BY_OBJECT_TYPE_QUESTION = "How many events of activity $ACT_X involve object type $OT_A?"
    UNIQUE_OBJECTS_BY_ACTIVITY_QUESTION = "How many unique objects interact with activity $ACT_X?"
    EDGE_COUNT_QUESTION = "How often does $ACT_X directly precede $ACT_Y for $OT_A?"
    EDGE_DURATION_QUESTION = "What is the average direct edge duration from $ACT_X to $ACT_Y for $OT_A?"
    EDGE_EXISTS_QUESTION = "Does the edge $ACT_X -> $ACT_Y exist for $OT_A?"
    EDGE_LABEL_QUESTION = "What is the edge label from $ACT_X to $ACT_Y?"
    OUTGOING_EDGES_QUESTION = "Which outgoing edges leave $ACT_X for $OT_A?"
    FALSE_EDGE_QUESTION = "Does the edge $ACT_Y -> $ACT_X exist for $OT_A?"
    BRANCHING_RATIO_QUESTION = "What share of outgoing edges from $ACT_X go to $ACT_Y for $OT_A?"
    OBJECT_INTERACTION_QUESTION = "Does $ACT_X interact with object types $OT_A and $OT_B?"

    def supported_templates(self):
        return [self.ACTIVITY_EVENTS_BY_OBJECT_TYPE_QUESTION,self.UNIQUE_OBJECTS_BY_ACTIVITY_QUESTION,self.EDGE_COUNT_QUESTION,self.EDGE_DURATION_QUESTION,self.EDGE_EXISTS_QUESTION,self.EDGE_LABEL_QUESTION,self.OUTGOING_EDGES_QUESTION,self.FALSE_EDGE_QUESTION,self.BRANCHING_RATIO_QUESTION,self.OBJECT_INTERACTION_QUESTION]

    def execute(self, question_template, model, bindings=None):
        bindings=bindings or {}
        if question_template == self.ACTIVITY_EVENTS_BY_OBJECT_TYPE_QUESTION:
            for name in ("$ACT_X","$OT_A"):
                missing=need(bindings,name)
                if missing: return missing
            act=bindings["$ACT_X"]; ot=bindings["$OT_A"]
            return ok(count_activity_for_type(model,act,ot), f"Counted {act} events for {ot}")
        if question_template == self.UNIQUE_OBJECTS_BY_ACTIVITY_QUESTION:
            missing=need(bindings,"$ACT_X")
            if missing: return missing
            act=bindings["$ACT_X"]
            return ok(len(unique_objects_for_activity(model,act)), f"Counted unique objects for {act}")
        if question_template in {self.EDGE_COUNT_QUESTION,self.EDGE_DURATION_QUESTION,self.EDGE_EXISTS_QUESTION,self.EDGE_LABEL_QUESTION,self.OUTGOING_EDGES_QUESTION,self.FALSE_EDGE_QUESTION,self.BRANCHING_RATIO_QUESTION,self.OBJECT_INTERACTION_QUESTION}:
            for name in ("$ACT_X","$ACT_Y","$OT_A"):
                missing=need(bindings,name)
                if missing: return missing
            x=bindings["$ACT_X"]; y=bindings["$ACT_Y"]; ot=bindings["$OT_A"]
            if question_template == self.EDGE_COUNT_QUESTION: val=edge_count(model,x,y,ot)
            elif question_template == self.EDGE_DURATION_QUESTION:
                vals=edge_durations(model,x,y,ot); val=mean(vals) if vals else None
            elif question_template == self.EDGE_EXISTS_QUESTION: val=edge_count(model,x,y,ot)>0
            elif question_template == self.EDGE_LABEL_QUESTION: val=f"{x} -> {y}"
            elif question_template == self.OUTGOING_EDGES_QUESTION: val=[f"{e.source} -> {e.target}" for e in model.directly_follows_edges.get(ot,()) if e.source==x]
            elif question_template == self.FALSE_EDGE_QUESTION: val=edge_count(model,y,x,ot)>0
            elif question_template == self.BRANCHING_RATIO_QUESTION:
                outgoing=sum(e.count for e in model.directly_follows_edges.get(ot,()) if e.source==x); val=(edge_count(model,x,y,ot)/outgoing) if outgoing else 0
            else:
                ot_b=bindings.get("$OT_B"); val=count_activity_for_type(model,x,ot)>0 and (not ot_b or count_activity_for_type(model,x,ot_b)>0)
            return ok(val, f"Computed Category 2 metric for {x}, {y}, {ot}")
        return err(f"Unsupported Category 2 question template: {question_template}")
