package com.qualitylab.api.defects;

import static com.qualitylab.api.client.IssueRequest.anIssue;

import com.qualitylab.api.base.BaseApiTest;
import com.qualitylab.api.models.Issue;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.testng.Assert;
import org.testng.annotations.Test;

/**
 * Each test states the CORRECT behaviour, so it fails while the planted bug exists and passes once it is
 * fixed. Not part of the default suite; see testng-known-defects.xml.
 */
public class KnownDefectsTest extends BaseApiTest {

    @Test(description = "BUG-001: PATCH must not move an issue to Closed without Verify")
    public void bug001PatchCannotCloseIssue() {
        Issue issue = reporter.createIssue(anIssue());
        int status = engineer.patch("/issues/" + issue.getId(), Map.of("state", "Closed")).statusCode();
        Assert.assertEquals(status, 422);
    }

    @Test(description = "BUG-002: an issue cannot be a duplicate of itself")
    public void bug002SelfDuplicateRejected() {
        Issue issue = reporter.createIssue(anIssue());
        int status = engineer.post("/issues/" + issue.getId() + "/duplicate",
                Map.of("duplicate_of", issue.getId())).statusCode();
        Assert.assertEquals(status, 422);
    }

    @Test(description = "BUG-003a: text search ignores case")
    public void bug003SearchIgnoresCase() {
        String tag = "Zq" + UUID.randomUUID().toString().replace("-", "").substring(0, 8);
        Issue issue = reporter.createIssue(anIssue().withTitle("Crash " + tag));
        List<Integer> ids = reporter.get("/issues", Map.of("q", tag.toLowerCase())).jsonPath().getList("id");
        Assert.assertEquals(ids, List.of(issue.getId()));
    }

    @Test(description = "BUG-003b: the P2 filter must not return P1 issues")
    public void bug003PriorityFilterIsExact() {
        String tag = "zq" + UUID.randomUUID().toString().replace("-", "").substring(0, 10);
        reporter.createIssue(anIssue().withTitle("Urgent " + tag).withPriority("P1"));
        Issue p2 = reporter.createIssue(anIssue().withTitle("Normal " + tag).withPriority("P2"));
        List<Integer> ids = reporter.get("/issues", Map.of("q", tag, "priority", "P2")).jsonPath().getList("id");
        Assert.assertEquals(ids, List.of(p2.getId()));
    }
}
