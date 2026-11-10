package com.qualitylab.api.models;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

/** An issue as returned by the API. Unknown JSON fields are ignored so new fields do not break the tests. */
@JsonIgnoreProperties(ignoreUnknown = true)
public class Issue {
    private int id;
    private String title;
    private String description;
    private String component;
    private String priority;
    private String state;
    private String reporter;
    private String assignee;

    @JsonProperty("duplicate_of")
    private Integer duplicateOf;

    public int getId() { return id; }
    public String getTitle() { return title; }
    public String getDescription() { return description; }
    public String getComponent() { return component; }
    public String getPriority() { return priority; }
    public String getState() { return state; }
    public String getReporter() { return reporter; }
    public String getAssignee() { return assignee; }
    public Integer getDuplicateOf() { return duplicateOf; }

    // Jackson needs setters (or field access) to fill the object.
    public void setId(int id) { this.id = id; }
    public void setTitle(String title) { this.title = title; }
    public void setDescription(String description) { this.description = description; }
    public void setComponent(String component) { this.component = component; }
    public void setPriority(String priority) { this.priority = priority; }
    public void setState(String state) { this.state = state; }
    public void setReporter(String reporter) { this.reporter = reporter; }
    public void setAssignee(String assignee) { this.assignee = assignee; }
    public void setDuplicateOf(Integer duplicateOf) { this.duplicateOf = duplicateOf; }
}
