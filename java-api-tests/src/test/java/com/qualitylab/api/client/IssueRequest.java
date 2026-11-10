package com.qualitylab.api.client;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.UUID;

/** Builds the JSON body for creating an issue. Sensible defaults, override only what a test cares about. */
public final class IssueRequest {
    private final Map<String, Object> fields = new LinkedHashMap<>();

    private IssueRequest() {
        fields.put("title", "Sync stalls on large mailbox " + UUID.randomUUID().toString().substring(0, 8));
        fields.put("description", "Spinner never stops");
        fields.put("component", "Mail > Sync");
        fields.put("priority", "P3");
    }

    public static IssueRequest anIssue() {
        return new IssueRequest();
    }

    public IssueRequest withTitle(String title) {
        fields.put("title", title);
        return this;
    }

    public IssueRequest withDescription(String description) {
        fields.put("description", description);
        return this;
    }

    public IssueRequest withComponent(String component) {
        fields.put("component", component);
        return this;
    }

    public IssueRequest withPriority(String priority) {
        fields.put("priority", priority);
        return this;
    }

    public IssueRequest without(String field) {
        fields.remove(field);
        return this;
    }

    public Map<String, Object> toBody() {
        return new LinkedHashMap<>(fields);
    }
}
