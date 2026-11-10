package com.qualitylab.api.tests;

import static org.hamcrest.Matchers.equalTo;
import static org.hamcrest.Matchers.not;
import static org.hamcrest.Matchers.emptyOrNullString;

import com.qualitylab.api.base.BaseApiTest;
import com.qualitylab.api.client.ApiClient;
import io.qameta.allure.Description;
import io.qameta.allure.Feature;
import java.util.Map;
import org.testng.Assert;
import org.testng.annotations.Test;

@Feature("Authentication")
public class AuthTest extends BaseApiTest {

    private String registerUser(String role) {
        String name = "auth_" + System.nanoTime();
        int status = anonymous.post("/users", Map.of("username", name, "password", "right-pass", "role", role))
                .statusCode();
        Assert.assertEquals(status, 201);
        return name;
    }

    @Test(groups = "smoke", description = "Health endpoint answers")
    public void healthEndpointIsUp() {
        Assert.assertEquals(anonymous.get("/health").statusCode(), 200);
    }

    @Test(groups = "smoke")
    @Description("A valid login returns a non-empty token")
    public void validLoginReturnsToken() {
        String name = registerUser("reporter");
        anonymous.post("/auth/login", Map.of("username", name, "password", "right-pass"))
                .then()
                .statusCode(200)
                .body("token", not(emptyOrNullString()));
    }

    @Test(groups = "regression")
    public void wrongPasswordIsForbidden() {
        String name = registerUser("reporter");
        int status = anonymous.post("/auth/login", Map.of("username", name, "password", "wrong")).statusCode();
        Assert.assertEquals(status, 403);
    }

    @Test(groups = "regression")
    public void unknownUserIsForbidden() {
        int status = anonymous.post("/auth/login", Map.of("username", "ghost_user", "password", "whatever"))
                .statusCode();
        Assert.assertEquals(status, 403);
    }

    @Test(groups = "regression")
    public void endpointsRequireAToken() {
        Assert.assertEquals(anonymous.get("/issues").statusCode(), 401);
    }

    @Test(groups = "regression")
    public void garbageTokenIsRejected() {
        Assert.assertEquals(new ApiClient(baseUrl, "garbage").get("/issues").statusCode(), 401);
    }

    @Test(groups = "regression")
    public void meReturnsRole() {
        engineer.get("/me").then().statusCode(200).body("role", equalTo("engineer"));
    }

    @Test(groups = "regression")
    public void duplicateUserIsConflict() {
        String name = "dup_" + System.nanoTime();
        Map<String, String> body = Map.of("username", name, "password", "abcd1234", "role", "qa");
        Assert.assertEquals(anonymous.post("/users", body).statusCode(), 201);
        Assert.assertEquals(anonymous.post("/users", body).statusCode(), 409);
    }
}
