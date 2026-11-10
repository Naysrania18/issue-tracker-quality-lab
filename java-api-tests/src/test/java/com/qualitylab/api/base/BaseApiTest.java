package com.qualitylab.api.base;

import com.qualitylab.api.client.ApiClient;
import com.qualitylab.api.models.Issue;
import com.qualitylab.api.models.Role;
import com.qualitylab.api.models.WorkflowState;
import java.util.Map;
import java.util.UUID;
import org.testng.annotations.BeforeClass;

/**
 * Common set-up. Works against any running, even empty, tracker: it creates its own users with a random
 * suffix and creates the components it needs (an "already exists" answer is fine).
 */
public abstract class BaseApiTest {
    protected static final String PASSWORD = "api-test-pass";

    protected String baseUrl;
    protected ApiClient anonymous;
    protected ApiClient reporter;
    protected ApiClient engineer;
    protected ApiClient qa;

    @BeforeClass(alwaysRun = true)
    public void setUpUsersAndComponents() {
        baseUrl = System.getProperty("tracker.url", "http://127.0.0.1:8000/api");
        String suffix = UUID.randomUUID().toString().substring(0, 6);
        anonymous = new ApiClient(baseUrl, null);
        reporter = ApiClient.loginAs(baseUrl, "rep_" + suffix, PASSWORD, Role.REPORTER.apiName());
        engineer = ApiClient.loginAs(baseUrl, "eng_" + suffix, PASSWORD, Role.ENGINEER.apiName());
        qa = ApiClient.loginAs(baseUrl, "qa_" + suffix, PASSWORD, Role.QA.apiName());
        ensureComponent("Mail", null);
        ensureComponent("Sync", "Mail");
        ensureComponent("Compose", "Mail");
        ensureComponent("Calendar", null);
    }

    private void ensureComponent(String name, String parent) {
        Map<String, Object> body = parent == null
                ? Map.of("name", name)
                : Map.of("name", name, "parent", parent);
        engineer.post("/components", body); // 201 created or 409 already there
    }

    /** Move an issue along the legal path until it reaches the target state. */
    protected void walkTo(Issue issue, WorkflowState target) {
        WorkflowState[] path = {
            WorkflowState.INTEGRATE, WorkflowState.BUILD, WorkflowState.VERIFY, WorkflowState.CLOSED
        };
        for (WorkflowState step : path) {
            ApiClient actor = step == WorkflowState.CLOSED ? qa : engineer;
            int status = actor.moveIssue(issue.getId(), step).statusCode();
            if (status != 200) {
                throw new AssertionError("Could not move issue " + issue.getId() + " to " + step + ": " + status);
            }
            if (step == target) {
                return;
            }
        }
    }
}
