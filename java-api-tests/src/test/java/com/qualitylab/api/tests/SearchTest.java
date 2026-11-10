package com.qualitylab.api.tests;

import static com.qualitylab.api.client.IssueRequest.anIssue;

import com.qualitylab.api.base.BaseApiTest;
import com.qualitylab.api.models.Issue;
import com.qualitylab.api.models.WorkflowState;
import io.qameta.allure.Feature;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.testng.Assert;
import org.testng.annotations.Test;

/** Each test tags its issues with a unique word so it only sees its own data on a shared server. */
@Feature("Search")
public class SearchTest extends BaseApiTest {

    private static String tag() {
        return "zq" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
    }

    private List<Integer> idsFor(Map<String, String> params) {
        return reporter.get("/issues", params).jsonPath().getList("id");
    }

    @Test(groups = "smoke")
    public void textSearchFindsIssueByTitle() {
        String tag = tag();
        Issue issue = reporter.createIssue(anIssue().withTitle("Crash on " + tag));
        Assert.assertEquals(idsFor(Map.of("q", tag)), List.of(issue.getId()));
    }

    @Test(groups = "regression")
    public void textSearchFindsIssueByDescription() {
        String tag = tag();
        Issue issue = reporter.createIssue(anIssue().withDescription("contains " + tag));
        Assert.assertEquals(idsFor(Map.of("q", tag)), List.of(issue.getId()));
    }

    @Test(groups = "regression")
    public void stateFilterOnlyReturnsThatState() {
        String tag = tag();
        Issue stays = reporter.createIssue(anIssue().withTitle("Stays " + tag));
        Issue moved = reporter.createIssue(anIssue().withTitle("Moved " + tag));
        engineer.moveIssue(moved.getId(), WorkflowState.INTEGRATE);
        Assert.assertEquals(idsFor(Map.of("q", tag, "state", "Integrate")), List.of(moved.getId()));
        Assert.assertEquals(idsFor(Map.of("q", tag, "state", "Analyze")), List.of(stays.getId()));
    }

    @Test(groups = "regression")
    public void parentComponentIncludesChildren() {
        String tag = tag();
        Issue sync = reporter.createIssue(anIssue().withTitle("A " + tag).withComponent("Mail > Sync"));
        Issue compose = reporter.createIssue(anIssue().withTitle("B " + tag).withComponent("Mail > Compose"));
        reporter.createIssue(anIssue().withTitle("C " + tag).withComponent("Calendar"));
        List<Integer> ids = idsFor(Map.of("q", tag, "component", "Mail"));
        Assert.assertEqualsNoOrder(ids.toArray(), new Object[] {sync.getId(), compose.getId()});
    }

    @Test(groups = "regression")
    public void childComponentIsNarrower() {
        String tag = tag();
        Issue sync = reporter.createIssue(anIssue().withTitle("A " + tag).withComponent("Mail > Sync"));
        reporter.createIssue(anIssue().withTitle("B " + tag).withComponent("Mail > Compose"));
        Assert.assertEquals(idsFor(Map.of("q", tag, "component", "Mail > Sync")), List.of(sync.getId()));
    }

    @Test(groups = "regression")
    public void noMatchGivesEmptyList() {
        Assert.assertTrue(idsFor(Map.of("q", tag())).isEmpty());
    }

    @Test(groups = "regression")
    public void unknownComponentFilterIsNotFound() {
        Assert.assertEquals(reporter.get("/issues", Map.of("component", "Nope")).statusCode(), 404);
    }
}
