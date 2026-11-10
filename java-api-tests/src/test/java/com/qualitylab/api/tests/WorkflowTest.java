package com.qualitylab.api.tests;

import static com.qualitylab.api.client.IssueRequest.anIssue;

import com.qualitylab.api.base.BaseApiTest;
import com.qualitylab.api.base.DataProviders;
import com.qualitylab.api.models.Issue;
import com.qualitylab.api.models.WorkflowState;
import io.qameta.allure.Feature;
import org.testng.Assert;
import org.testng.annotations.Test;

@Feature("Workflow")
public class WorkflowTest extends BaseApiTest {

    @Test(groups = "smoke")
    public void issueWalksThroughEveryStateToClosed() {
        Issue issue = reporter.createIssue(anIssue());
        walkTo(issue, WorkflowState.CLOSED);
        Assert.assertEquals(reporter.getIssue(issue.getId()).getState(), "Closed");
    }

    /**
     * Drives every (from, to) pair: put an issue into 'from' using the legal path, try to move to 'to',
     * and check the API agrees with the documented rules. The pair (Closed, *) first closes the issue.
     */
    @Test(groups = "regression", dataProvider = "allTransitions", dataProviderClass = DataProviders.class)
    public void transitionMatchesRules(WorkflowState from, WorkflowState to, boolean allowed) {
        Issue issue = reporter.createIssue(anIssue());
        if (from != WorkflowState.ANALYZE) {
            walkTo(issue, from);
        }
        // QA may do anything an engineer may, and is the only role allowed to close.
        int status = qa.moveIssue(issue.getId(), to).statusCode();
        Assert.assertEquals(status, allowed ? 200 : 422,
                "move " + from + " -> " + to + " should be " + (allowed ? "allowed" : "rejected"));
    }

    @Test(groups = "regression")
    public void engineerCannotClose() {
        Issue issue = reporter.createIssue(anIssue());
        walkTo(issue, WorkflowState.VERIFY);
        Assert.assertEquals(engineer.moveIssue(issue.getId(), WorkflowState.CLOSED).statusCode(), 422);
        Assert.assertEquals(reporter.getIssue(issue.getId()).getState(), "Verify");
    }

    @Test(groups = "regression")
    public void reporterCannotChangeState() {
        Issue issue = reporter.createIssue(anIssue());
        Assert.assertEquals(reporter.moveIssue(issue.getId(), WorkflowState.INTEGRATE).statusCode(), 403);
    }

    @Test(groups = "regression")
    public void unknownStateIsRejected() {
        Issue issue = reporter.createIssue(anIssue());
        int status = engineer.post("/issues/" + issue.getId() + "/transition", java.util.Map.of("target", "Teleport"))
                .statusCode();
        Assert.assertEquals(status, 422);
    }

    @Test(groups = "regression")
    public void everyMoveIsWrittenToHistory() {
        Issue issue = reporter.createIssue(anIssue());
        engineer.moveIssue(issue.getId(), WorkflowState.INTEGRATE);
        var history = reporter.get("/issues/" + issue.getId() + "/history").jsonPath();
        Assert.assertEquals(history.getString("[-1].old_value"), "Analyze");
        Assert.assertEquals(history.getString("[-1].new_value"), "Integrate");
    }
}
