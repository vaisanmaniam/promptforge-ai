"""
NetworkX-backed Directed Traceability Graph Engine.
Constructs, validates, and analyzes bidirectional traceability between
prompts, requirements, and dependencies, with cycle detection and impact analysis.
"""

from typing import Dict, List, Set
import networkx as nx

from app.schemas.requirement import (
    ImpactAnalysisReport,
    RequirementSpecification,
    TraceabilityEdge,
    TraceabilityGraph,
    TraceabilityNode,
)


class TraceabilityGraphEngine:
    """
    Engine for modeling and querying software requirement traceability graphs using NetworkX.
    """

    PROMPT_ROOT_ID = "PROMPT-ROOT"

    def build_networkx_graph(self, spec: RequirementSpecification) -> nx.DiGraph:
        """
        Constructs an in-memory NetworkX directed graph from a RequirementSpecification.
        """
        graph = nx.DiGraph()

        # Add root prompt node
        graph.add_node(
            self.PROMPT_ROOT_ID,
            type="prompt",
            label="Source Prompt",
            category="prompt",
            status="source",
            priority="none",
            metadata={"title": spec.title, "length": len(spec.source_prompt)},
        )

        # Add requirement nodes
        for req in spec.requirements:
            graph.add_node(
                req.id,
                type="requirement",
                label=f"{req.id}: {req.title}",
                category=req.category.value,
                status=req.status.value,
                priority=req.priority.value,
                metadata={
                    "description": req.description,
                    "verification_state": req.verification_state.value,
                    "ac_count": len(req.acceptance_criteria),
                    "assumptions_count": len(req.assumptions),
                },
            )

            # Edge from prompt to requirement (generates)
            graph.add_edge(self.PROMPT_ROOT_ID, req.id, relation="generates")

        # Add requirement-to-requirement dependencies
        for req in spec.requirements:
            for dep_id in req.depends_on:
                if graph.has_node(dep_id):
                    # req depends on dep_id -> directed edge from dependent to prerequisite
                    graph.add_edge(req.id, dep_id, relation="depends_on")

            for ref_id in req.refines:
                if graph.has_node(ref_id):
                    graph.add_edge(req.id, ref_id, relation="refines")

        return graph

    def export_graph(self, spec: RequirementSpecification) -> TraceabilityGraph:
        """
        Exports the NetworkX graph as a schema-compliant TraceabilityGraph for UI visualization.
        """
        graph = self.build_networkx_graph(spec)

        nodes: List[TraceabilityNode] = []
        for node_id, data in graph.nodes(data=True):
            nodes.append(
                TraceabilityNode(
                    id=node_id,
                    type=data.get("type", "requirement"),
                    label=data.get("label", node_id),
                    category=data.get("category"),
                    status=data.get("status"),
                    priority=data.get("priority"),
                    metadata=data.get("metadata", {}),
                )
            )

        edges: List[TraceabilityEdge] = []
        for u, v, data in graph.edges(data=True):
            edges.append(
                TraceabilityEdge(
                    source=u,
                    target=v,
                    relation=data.get("relation", "depends_on"),
                )
            )

        # Detect cycles specifically among requirement nodes (excluding prompt root)
        sub_graph = graph.copy()
        if sub_graph.has_node(self.PROMPT_ROOT_ID):
            sub_graph.remove_node(self.PROMPT_ROOT_ID)

        cycles: List[List[str]] = []
        try:
            cycles = list(nx.simple_cycles(sub_graph))
        except Exception:
            cycles = []

        isolated: List[str] = [
            n for n in sub_graph.nodes() if sub_graph.degree(n) == 0
        ]

        return TraceabilityGraph(
            nodes=nodes,
            edges=edges,
            has_cycles=len(cycles) > 0,
            cycle_paths=cycles,
            isolated_nodes=isolated,
        )

    def analyze_impact(
        self, spec: RequirementSpecification, target_req_id: str
    ) -> ImpactAnalysisReport:
        """
        Conducts blast-radius impact analysis for a given requirement.
        - Upstream dependencies: Requirements target_req_id depends on.
        - Downstream dependents: Requirements that depend on target_req_id (would be affected if changed).
        """
        graph = self.build_networkx_graph(spec)

        if not graph.has_node(target_req_id):
            return ImpactAnalysisReport(
                target_req_id=target_req_id,
                upstream_dependencies=[],
                downstream_dependents=[],
                impact_depth=0,
                risk_level="low",
            )

        # Upstream: target_req_id -> dep_id edges with relation 'depends_on'
        # In our graph, req -> dep means req depends on dep.
        # So upstream dependencies of target_req are successors in the dependency subgraph.
        dep_graph = nx.DiGraph()
        for u, v, data in graph.edges(data=True):
            if data.get("relation") == "depends_on":
                dep_graph.add_edge(u, v)

        upstream: List[str] = []
        if dep_graph.has_node(target_req_id):
            upstream = list(nx.descendants(dep_graph, target_req_id))

        # Downstream: other requirements that depend on target_req_id.
        # Those are ancestors in dep_graph (nodes with a path to target_req_id).
        downstream: List[str] = []
        if dep_graph.has_node(target_req_id):
            downstream = list(nx.ancestors(dep_graph, target_req_id))

        # Calculate impact depth (longest path from any downstream dependent to target)
        depth = 0
        if downstream:
            for node in downstream:
                try:
                    path_len = nx.shortest_path_length(dep_graph, source=node, target=target_req_id)
                    depth = max(depth, path_len)
                except (nx.NetworkXNoPath, nx.NodeNotFound):
                    pass

        # Risk level determination
        target_item = next((r for r in spec.requirements if r.id == target_req_id), None)
        base_priority = target_item.priority.value if target_item else "medium"

        if len(downstream) > 4 or (len(downstream) >= 2 and base_priority == "critical"):
            risk = "critical"
        elif len(downstream) >= 2 or base_priority == "high":
            risk = "high"
        elif len(downstream) == 1:
            risk = "medium"
        else:
            risk = "low"

        return ImpactAnalysisReport(
            target_req_id=target_req_id,
            upstream_dependencies=upstream,
            downstream_dependents=downstream,
            impact_depth=depth,
            risk_level=risk,
        )
