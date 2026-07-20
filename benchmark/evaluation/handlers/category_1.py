from __future__ import annotations
from .base import count_activity_for_type, edge_count, end_activities, err, need, object_ids, ok, start_activities

class Category1Handler:
    TOTAL_EVENTS_QUESTION = "How many events are in the log?"
    OBJECTS_BY_TYPE_QUESTION = "How many objects of type $OT_A are in the log?"
    NODE_OUT_DEGREE_QUESTION = "What is the out-degree of activity $ACT_X for object type $OT_A in the OC-DFG?"
    NODE_IN_DEGREE_QUESTION = "What is the in-degree of activity $ACT_X for object type $OT_A in the OC-DFG?"
    START_FREQUENCY_QUESTION = "How often does activity $ACT_X start an object of type $OT_A?"
    ACTIVITY_FREQUENCY_QUESTION = "How often does activity $ACT_X occur for object type $OT_A?"
    END_FREQUENCY_QUESTION = "How often does activity $ACT_X end an object of type $OT_A?"
    ZERO_IN_QUESTION = "Which activities have zero in-degree for object type $OT_A?"
    ZERO_OUT_QUESTION = "Which activities have zero out-degree for object type $OT_A?"
    NODE_OBJECT_COUNT_QUESTION = "How many $OT_A objects interact with activity $ACT_X?"
    DIRECT_EDGE_EXISTS_QUESTION = "Is there a direct transition from $ACT_X to $ACT_Y for object type $OT_A?"

    def supported_templates(self):
        return [self.TOTAL_EVENTS_QUESTION,self.OBJECTS_BY_TYPE_QUESTION,self.NODE_OUT_DEGREE_QUESTION,self.NODE_IN_DEGREE_QUESTION,self.START_FREQUENCY_QUESTION,self.ACTIVITY_FREQUENCY_QUESTION,self.END_FREQUENCY_QUESTION,self.ZERO_IN_QUESTION,self.ZERO_OUT_QUESTION,self.NODE_OBJECT_COUNT_QUESTION,self.DIRECT_EDGE_EXISTS_QUESTION]

    def execute(self, question_template, model, bindings=None):
        bindings = bindings or {}
        if question_template == self.TOTAL_EVENTS_QUESTION:
            return {"value": len(model.events), "status": "success", "message": "Computed total event count from ReferenceModel.events"}
        if question_template == self.OBJECTS_BY_TYPE_QUESTION:
            missing = need(bindings, "$OT_A")
            if missing: return missing
            ot=bindings["$OT_A"]
            return ok(len(object_ids(model, ot)), f"Counted objects of type {ot}")
        if question_template in {self.NODE_OUT_DEGREE_QUESTION,self.NODE_IN_DEGREE_QUESTION,self.START_FREQUENCY_QUESTION,self.ACTIVITY_FREQUENCY_QUESTION,self.END_FREQUENCY_QUESTION,self.NODE_OBJECT_COUNT_QUESTION,self.DIRECT_EDGE_EXISTS_QUESTION}:
            for name in ("$OT_A", "$ACT_X"):
                missing=need(bindings,name)
                if missing: return missing
            ot=bindings["$OT_A"]; act=bindings["$ACT_X"]
            if question_template == self.NODE_OUT_DEGREE_QUESTION:
                val=sum(1 for e in model.directly_follows_edges.get(ot,()) if e.source==act)
            elif question_template == self.NODE_IN_DEGREE_QUESTION:
                val=sum(1 for e in model.directly_follows_edges.get(ot,()) if e.target==act)
            elif question_template == self.START_FREQUENCY_QUESTION:
                val=sum(1 for oid in object_ids(model,ot) if model.events_for_object(oid) and model.events_for_object(oid)[0].activity==act)
            elif question_template == self.ACTIVITY_FREQUENCY_QUESTION:
                val=count_activity_for_type(model,act,ot)
            elif question_template == self.END_FREQUENCY_QUESTION:
                val=sum(1 for oid in object_ids(model,ot) if model.events_for_object(oid) and model.events_for_object(oid)[-1].activity==act)
            elif question_template == self.NODE_OBJECT_COUNT_QUESTION:
                val=count_activity_for_type(model,act,ot)
            else:
                missing=need(bindings,"$ACT_Y")
                if missing: return missing
                val=edge_count(model,act,bindings["$ACT_Y"],ot)>0
            return ok(val, f"Computed Category 1 metric for {act} and {ot}")
        if question_template == self.ZERO_IN_QUESTION:
            missing=need(bindings,"$OT_A")
            if missing: return missing
            ot=bindings["$OT_A"]; targets={e.target for e in model.directly_follows_edges.get(ot,())}; vals=[a for a in model.activities if count_activity_for_type(model,a,ot) and a not in targets]
            return ok(vals, f"Computed zero in-degree activities for {ot}")
        if question_template == self.ZERO_OUT_QUESTION:
            missing=need(bindings,"$OT_A")
            if missing: return missing
            ot=bindings["$OT_A"]; sources={e.source for e in model.directly_follows_edges.get(ot,())}; vals=[a for a in model.activities if count_activity_for_type(model,a,ot) and a not in sources]
            return ok(vals, f"Computed zero out-degree activities for {ot}")
        return err(f"Unsupported Category 1 question template: {question_template}")
