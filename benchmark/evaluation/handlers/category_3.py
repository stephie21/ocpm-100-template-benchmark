from __future__ import annotations
from .base import edge_count, err, need, ok, reachable, shortest_path

class Category3Handler:
    DIRECTLY_FOLLOWS_QUESTION = "How often does activity $ACT_Y directly precede $ACT_X for object type $OT_A?"
    REACHABLE_QUESTION = "Can $ACT_X eventually reach $ACT_Y for $OT_A?"
    NOT_REACHABLE_QUESTION = "Can $ACT_Y eventually reach $ACT_X for $OT_A?"
    PATH_EXISTS_QUESTION = "Is there a path between $ACT_X and $ACT_Y for $OT_A?"
    PATH_LENGTH_QUESTION = "How many activities are on the path from $ACT_X to $ACT_Y for $OT_A?"
    SHORTEST_PATH_QUESTION = "What is the shortest path from $ACT_X to $ACT_Y for $OT_A?"
    DOWNSTREAM_QUESTION = "Which activities are downstream of $ACT_X for $OT_A?"
    SUBGRAPH_QUESTION = "Which activities form the local subgraph around $ACT_X for $OT_A?"
    START_REACHES_END_QUESTION = "Does $ACT_X reach $ACT_Y in the lifecycle?"
    HAS_DIRECT_EDGE_QUESTION = "Is there a direct path from $ACT_X to $ACT_Y?"
    ACTIVITY_COUNT_QUESTION = "How many activities are in the reachable subgraph?"
    EDGE_LIST_QUESTION = "Which direct edges are on the path?"

    def supported_templates(self):
        return [self.DIRECTLY_FOLLOWS_QUESTION,self.REACHABLE_QUESTION,self.NOT_REACHABLE_QUESTION,self.PATH_EXISTS_QUESTION,self.PATH_LENGTH_QUESTION,self.SHORTEST_PATH_QUESTION,self.DOWNSTREAM_QUESTION,self.SUBGRAPH_QUESTION,self.START_REACHES_END_QUESTION,self.HAS_DIRECT_EDGE_QUESTION,self.ACTIVITY_COUNT_QUESTION,self.EDGE_LIST_QUESTION]

    def execute(self, question_template, model, bindings=None):
        bindings=bindings or {}
        if question_template not in self.supported_templates():
            return err(f"Unsupported Category 3 question template: {question_template}")
        for name in ("$ACT_X","$ACT_Y","$OT_A"):
            missing=need(bindings,name)
            if missing: return missing
        x=bindings["$ACT_X"]; y=bindings["$ACT_Y"]; ot=bindings["$OT_A"]
        if question_template == self.DIRECTLY_FOLLOWS_QUESTION:
            val=edge_count(model,y,x,ot)
        elif question_template == self.NOT_REACHABLE_QUESTION:
            val=reachable(model,y,x,ot)
        elif question_template in {self.REACHABLE_QUESTION,self.PATH_EXISTS_QUESTION,self.START_REACHES_END_QUESTION}:
            val=reachable(model,x,y,ot)
        elif question_template == self.HAS_DIRECT_EDGE_QUESTION:
            val=edge_count(model,x,y,ot)>0
        elif question_template == self.PATH_LENGTH_QUESTION:
            val=max(0,len(shortest_path(model,x,y,ot))-1)
        elif question_template == self.SHORTEST_PATH_QUESTION:
            val=shortest_path(model,x,y,ot)
        elif question_template == self.DOWNSTREAM_QUESTION:
            val=sorted([a for a in model.activities if a != x and reachable(model,x,a,ot)])
        elif question_template == self.SUBGRAPH_QUESTION:
            val=[x] + sorted({edge.target for edge in model.directly_follows_edges.get(ot,()) if edge.source==x})
        elif question_template == self.ACTIVITY_COUNT_QUESTION:
            val=len([a for a in model.activities if a != x and reachable(model,x,a,ot)])
        else:
            path=shortest_path(model,x,y,ot); val=[f"{a} -> {b}" for a,b in zip(path,path[1:])]
        return ok(val, f"Computed Category 3 metric for {x}, {y}, {ot}")
