package com.qualitylab.api.tests;

import static com.qualitylab.api.client.IssueRequest.anIssue;

import com.qualitylab.api.base.BaseApiTest;
import com.qualitylab.api.base.DataProviders;
import com.qualitylab.api.models.Issue;
import io.qameta.allure.Feature;
import io.restassured.response.Response;
import java.util.List;
import java.util.Map;
import org.testng.Assert;
import org.testng.annotations.Test;

@Feature("Issues")
public class IssueTest extends BaseApiTest {

    @Test(groups = "smoke")
    public void createdIssueStartsInAnalyze() {
        Issue created = reporter.createIssue(anIssue().withPriority("P1"));
        Assert.assertEquals(created.getState(), "Analyze");
        Assert.assertEquals(created.getPriority(), "P1");
        Assert.assertEquals(created.getComponent(), "Mail > Sync");
        Assert.assertTrue(created.getId() > 0);
    }

    @Test(groups = "regression")
    public void issueCanBeReadBack() {
        Issue created = reporter.createIssue(anIssue());
        Issue fetched = reporter.getIssue(created.getId());
        Assert.assertEquals(fetched.getTitle(), created.getTitle());
    }

    @Test(groups = "regression", dataProvider = "invalidIssues", dataProviderClass = DataProviders.class)
    public void invalidIssueIsRejected(String why, String title, String component, String priority) {
        Response response = reporter.post("/issues", anIssue()
                .withTitle(title).withComponent(component).withPriority(priority).toBody());
        Assert.assertEquals(response.statusCode(), 422, why);
    }

    @Test(groups = "regression")
    public void missingTitleIsRejected() {
        Assert.assertEquals(reporter.post("/issues", anIssue().without("title").toBody()).statusCode(), 422);
    }

    @Test(groups = "regression")
    public void unknownComponentIsNotFound() {
        Assert.assertEquals(
                reporter.post("/issues", anIssue().withComponent("No > Such").toBody()).statusCode(), 404);
    }

    @Test(groups = "regression")
    public void missingIssueIsNotFound() {
        Assert.assertEquals(reporter.get("/issues/999999").statusCode(), 404);
    }

    @Test(groups = "regression")
    public void reporterCannotPatch() {
        Issue issue = reporter.createIssue(anIssue());
        Assert.assertEquals(reporter.patch("/issues/" + issue.getId(), Map.of("priority", "P1")).statusCode(), 403);
    }

    @Test(groups = "regression")
    public void engineerCanChangePriority() {
        Issue issue = reporter.createIssue(anIssue().withPriority("P4"));
        Issue updated = engineer.patch("/issues/" + issue.getId(), Map.of("priority", "P2")).as(Issue.class);
        Assert.assertEquals(updated.getPriority(), "P2");
    }

    @Test(groups = "regression")
    public void commentsAreStoredInOrder() {
        Issue issue = reporter.createIssue(anIssue());
        reporter.post("/issues/" + issue.getId() + "/comments", Map.of("body", "first"));
        engineer.post("/issues/" + issue.getId() + "/comments", Map.of("body", "second"));
        List<String> bodies = reporter.get("/issues/" + issue.getId() + "/comments").jsonPath().getList("body");
        Assert.assertEquals(bodies, List.of("first", "second"));
    }

    @Test(groups = "regression")
    public void emptyCommentIsRejected() {
        Issue issue = reporter.createIssue(anIssue());
        Assert.assertEquals(reporter.post("/issues/" + issue.getId() + "/comments", Map.of("body", "")).statusCode(), 422);
    }

    @Test(groups = "regression")
    public void duplicateCanBeMarkedByEngineerOnly() {
        Issue original = reporter.createIssue(anIssue());
        Issue copy = reporter.createIssue(anIssue());
        String path = "/issues/" + copy.getId() + "/duplicate";
        Map<String, Object> body = Map.of("duplicate_of", original.getId());
        Assert.assertEquals(reporter.post(path, body).statusCode(), 403);
        Response response = engineer.post(path, body);
        Assert.assertEquals(response.statusCode(), 200);
        Assert.assertEquals(response.as(Issue.class).getDuplicateOf(), Integer.valueOf(original.getId()));
    }

    @Test(groups = "regression")
    public void duplicateOfMissingIssueIsNotFound() {
        Issue issue = reporter.createIssue(anIssue());
        Assert.assertEquals(
                engineer.post("/issues/" + issue.getId() + "/duplicate", Map.of("duplicate_of", 999999)).statusCode(),
                404);
    }
}
