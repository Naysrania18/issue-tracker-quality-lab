package com.qualitylab.api.models;

import java.util.Map;
import java.util.Set;

/** Workflow states and the legal moves between them (mirrors the rules the tracker documents). */
public enum WorkflowState {
    ANALYZE("Analyze"),
    INTEGRATE("Integrate"),
    BUILD("Build"),
    VERIFY("Verify"),
    CLOSED("Closed");

    private static final Map<WorkflowState, Set<WorkflowState>> LEGAL = Map.of(
            ANALYZE, Set.of(INTEGRATE),
            INTEGRATE, Set.of(BUILD, ANALYZE),
            BUILD, Set.of(VERIFY, INTEGRATE),
            VERIFY, Set.of(CLOSED, ANALYZE),
            CLOSED, Set.of(ANALYZE));

    private final String apiName;

    WorkflowState(String apiName) {
        this.apiName = apiName;
    }

    public String apiName() {
        return apiName;
    }

    public boolean canMoveTo(WorkflowState target) {
        return LEGAL.get(this).contains(target);
    }
}
