package com.qualitylab.api.tests;

import static com.qualitylab.api.client.IssueRequest.anIssue;

import com.qualitylab.api.base.BaseApiTest;
import com.qualitylab.api.models.Issue;
import io.qameta.allure.Feature;
import io.restassured.response.Response;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.testng.Assert;
import org.testng.annotations.Test;

@Feature("Test management")
public class TestManagementTest extends BaseApiTest {

    private int newCase(String component) {
        return qa.post("/test-cases", Map.of("title", "Case " + UUID.randomUUID(), "component", component))
                .jsonPath().getInt("id");
    }

    private int newSuite(int... caseIds) {
        List<Integer> ids = java.util.Arrays.stream(caseIds).boxed().toList();
        return qa.post("/suites", Map.of("name", "Suite " + UUID.randomUUID(), "case_ids", ids))
                .jsonPath().getInt("id");
    }

    private int newRun(int suiteId) {
        return qa.post("/test-runs", Map.of("suite_id", suiteId)).jsonPath().getInt("id");
    }

    @Test(groups = "smoke")
    public void runWithOnlyPassesIsPassed() {
        int caseId = newCase("Mail > Sync");
        int runId = newRun(newSuite(caseId));
        qa.post("/test-runs/" + runId + "/results", Map.of("case_id", caseId, "status", "passed"));
        Assert.assertEquals(qa.post("/test-runs/" + runId + "/complete").jsonPath().getString("status"), "passed");
    }

    @Test(groups = "regression")
    public void oneFailureFailsTheRun() {
        Issue issue = reporter.createIssue(anIssue());
        int caseId = newCase("Mail > Sync");
        int runId = newRun(newSuite(caseId));
        qa.post("/test-runs/" + runId + "/results",
                Map.of("case_id", caseId, "status", "failed", "issue_id", issue.getId()));
        Assert.assertEquals(qa.post("/test-runs/" + runId + "/complete").jsonPath().getString("status"), "failed");
    }

    @Test(groups = "regression")
    public void onlyQaCanCreateCases() {
        Response response = engineer.post("/test-cases", Map.of("title", "Not allowed", "component", "Mail"));
        Assert.assertEquals(response.statusCode(), 403);
    }

    @Test(groups = "regression")
    public void cannotAddResultAfterCompletion() {
        int caseId = newCase("Calendar");
        int runId = newRun(newSuite(caseId));
        qa.post("/test-runs/" + runId + "/complete");
        int status = qa.post("/test-runs/" + runId + "/results", Map.of("case_id", caseId, "status", "passed"))
                .statusCode();
        Assert.assertEquals(status, 409);
    }

    @Test(groups = "regression")
    public void resultForCaseOutsideSuiteIsRejected() {
        int inSuite = newCase("Mail");
        int outside = newCase("Calendar");
        int runId = newRun(newSuite(inSuite));
        int status = qa.post("/test-runs/" + runId + "/results", Map.of("case_id", outside, "status", "passed"))
                .statusCode();
        Assert.assertEquals(status, 404);
    }

    @Test(groups = "regression")
    public void suiteWithUnknownCaseIsNotFound() {
        int status = qa.post("/suites", Map.of("name", "Bad " + UUID.randomUUID(), "case_ids", List.of(999999)))
                .statusCode();
        Assert.assertEquals(status, 404);
    }

    @Test(groups = "regression")
    public void negativeDurationIsRejected() {
        int caseId = newCase("Mail");
        int runId = newRun(newSuite(caseId));
        int status = qa.post("/test-runs/" + runId + "/results",
                Map.of("case_id", caseId, "status", "passed", "duration_ms", -1)).statusCode();
        Assert.assertEquals(status, 422);
    }
}
