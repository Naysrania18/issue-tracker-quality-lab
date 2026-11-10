package com.qualitylab.api.models;

/** The three user roles of the tracker. */
public enum Role {
    REPORTER("reporter"),
    ENGINEER("engineer"),
    QA("qa");

    private final String apiName;

    Role(String apiName) {
        this.apiName = apiName;
    }

    public String apiName() {
        return apiName;
    }
}
