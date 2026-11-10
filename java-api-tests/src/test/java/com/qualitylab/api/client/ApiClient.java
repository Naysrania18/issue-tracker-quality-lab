package com.qualitylab.api.client;

import static io.restassured.RestAssured.given;

import com.qualitylab.api.models.Issue;
import com.qualitylab.api.models.WorkflowState;
import io.qameta.allure.restassured.AllureRestAssured;
import io.restassured.http.ContentType;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;
import java.util.Map;

/**
 * A logged-in user talking to the tracker. Each method returns the raw Response so tests can assert on
 * status codes (including error cases) as well as the body.
 */
public class ApiClient {
    private final String baseUrl;
    private final String token; // null for an anonymous client

    public ApiClient(String baseUrl, String token) {
        this.baseUrl = baseUrl;
        this.token = token;
    }

    /** Create the user if needed, log in and return a client holding the token. */
    public static ApiClient loginAs(String baseUrl, String username, String password, String role) {
        ApiClient anonymous = new ApiClient(baseUrl, null);
        anonymous.post("/users", Map.of("username", username, "password", password, "role", role)); // 409 is fine
        Response login = anonymous.post("/auth/login", Map.of("username", username, "password", password));
        return new ApiClient(baseUrl, login.jsonPath().getString("token"));
    }

    private RequestSpecification spec() {
        RequestSpecification spec = given()
                .baseUri(baseUrl)
                .contentType(ContentType.JSON)
                .filter(new AllureRestAssured());
        return token == null ? spec : spec.header("Authorization", "Bearer " + token);
    }

    public Response get(String path) {
        return spec().get(path);
    }

    public Response get(String path, Map<String, ?> queryParams) {
        return spec().queryParams(queryParams).get(path);
    }

    public Response post(String path, Object body) {
        return spec().body(body).post(path);
    }

    public Response post(String path) {
        return spec().post(path);
    }

    public Response patch(String path, Object body) {
        return spec().body(body).patch(path);
    }

    // ---- convenience wrappers for the calls almost every test needs ----

    public Issue createIssue(IssueRequest request) {
        Response response = post("/issues", request.toBody());
        if (response.statusCode() != 201) {
            throw new AssertionError("Could not create issue: " + response.statusCode() + " " + response.asString());
        }
        return response.as(Issue.class);
    }

    public Response moveIssue(int issueId, WorkflowState target) {
        return post("/issues/" + issueId + "/transition", Map.of("target", target.apiName()));
    }

    public Issue getIssue(int issueId) {
        return get("/issues/" + issueId).as(Issue.class);
    }
}
