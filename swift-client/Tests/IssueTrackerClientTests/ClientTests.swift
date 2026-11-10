import XCTest
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
@testable import IssueTrackerClient

final class ClientTests: XCTestCase {
    private var transport: MockTransport!
    private var client: IssueTrackerClient!

    override func setUp() {
        super.setUp()
        transport = MockTransport()
        client = IssueTrackerClient(
            baseURL: URL(string: "http://tracker.test/api")!, token: "abc123", transport: transport)
    }

    // MARK: Decoding

    func testGetIssueDecodesSnakeCaseFields() async throws {
        transport.enqueue(json: Fixtures.issueJSON)
        let issue = try await client.getIssue(id: 7)
        XCTAssertEqual(issue.id, 7)
        XCTAssertEqual(issue.stepsToReproduce, "1. Open mailbox")
        XCTAssertEqual(issue.priority, .p2)
        XCTAssertEqual(issue.state, .analyze)
        XCTAssertNil(issue.assignee)
        XCTAssertNil(issue.duplicateOf)
    }

    func testListIssuesDecodesAnArray() async throws {
        transport.enqueue(json: Fixtures.issuesJSON(3))
        let issues = try await client.listIssues()
        XCTAssertEqual(issues.count, 3)
    }

    func testEmptyListIsFine() async throws {
        transport.enqueue(json: "[]")
        let issues = try await client.listIssues()
        XCTAssertTrue(issues.isEmpty)
    }

    func testMalformedBodyIsADecodingError() async {
        transport.enqueue(json: "{\"id\": \"not a number\"}")
        await assertThrows(APIError.decoding) { _ = try await self.client.getIssue(id: 1) }
    }

    func testUnknownStateInResponseIsADecodingError() async {
        transport.enqueue(json: Fixtures.issueJSON.replacingOccurrences(of: "Analyze", with: "Sleeping"))
        await assertThrows(APIError.decoding) { _ = try await self.client.getIssue(id: 7) }
    }

    // MARK: Request building

    func testRequestCarriesTokenAndAcceptHeader() async throws {
        transport.enqueue(json: Fixtures.issueJSON)
        _ = try await client.getIssue(id: 7)
        XCTAssertEqual(transport.lastRequest.httpMethod, "GET")
        XCTAssertEqual(transport.lastRequest.url?.absoluteString, "http://tracker.test/api/issues/7")
        XCTAssertEqual(transport.lastRequest.value(forHTTPHeaderField: "Authorization"), "Bearer abc123")
        XCTAssertEqual(transport.lastRequest.value(forHTTPHeaderField: "Accept"), "application/json")
    }

    func testNoAuthorizationHeaderWithoutToken() throws {
        let anonymous = IssueTrackerClient(baseURL: URL(string: "http://tracker.test/api")!, transport: transport)
        let request = try anonymous.makeRequest(method: "GET", path: "/health")
        XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
    }

    func testListIssuesBuildsQueryString() async throws {
        transport.enqueue(json: "[]")
        _ = try await client.listIssues(text: "crash", state: .verify, priority: .p1)
        let items = URLComponents(url: transport.lastRequest.url!, resolvingAgainstBaseURL: false)?.queryItems ?? []
        let pairs = Dictionary(uniqueKeysWithValues: items.map { ($0.name, $0.value ?? "") })
        XCTAssertEqual(pairs, ["q": "crash", "state": "Verify", "priority": "P1"])
    }

    func testListIssuesWithoutFiltersHasNoQuery() async throws {
        transport.enqueue(json: "[]")
        _ = try await client.listIssues()
        XCTAssertNil(transport.lastRequest.url?.query)
    }

    func testCreateIssueSendsSnakeCaseJSON() async throws {
        transport.enqueue(status: 201, json: Fixtures.issueJSON)
        let created = try await client.createIssue(
            NewIssue(title: "Sync hangs", component: "Mail > Sync", priority: .p2, stepsToReproduce: "1. Open"))
        XCTAssertEqual(created.id, 7)
        XCTAssertEqual(transport.lastRequest.httpMethod, "POST")
        XCTAssertEqual(transport.lastRequest.value(forHTTPHeaderField: "Content-Type"), "application/json")
        let body = try XCTUnwrap(transport.lastBodyJSON)
        XCTAssertEqual(body["title"] as? String, "Sync hangs")
        XCTAssertEqual(body["priority"] as? String, "P2")
        XCTAssertEqual(body["steps_to_reproduce"] as? String, "1. Open")
        XCTAssertNil(body["stepsToReproduce"])
    }

    func testAddCommentPostsBody() async throws {
        transport.enqueue(status: 201, json: "{\"author\": \"rita\", \"body\": \"Seen again\", \"created_at\": \"now\"}")
        let comment = try await client.addComment(issueID: 7, body: "Seen again")
        XCTAssertEqual(comment.author, "rita")
        XCTAssertEqual(transport.lastRequest.url?.path, "/api/issues/7/comments")
        XCTAssertEqual(transport.lastBodyJSON?["body"] as? String, "Seen again")
    }

    // MARK: Login

    func testLoginStoresTokenForLaterCalls() async throws {
        let fresh = IssueTrackerClient(baseURL: URL(string: "http://tracker.test/api")!, transport: transport)
        transport.enqueue(json: "{\"token\": \"new-token\"}")
        let token = try await fresh.login(username: "erin", password: "pw")
        XCTAssertEqual(token, "new-token")
        XCTAssertEqual(fresh.token, "new-token")
        XCTAssertEqual(transport.lastBodyJSON?["username"] as? String, "erin")

        transport.enqueue(json: "[]")
        _ = try await fresh.listIssues()
        XCTAssertEqual(transport.lastRequest.value(forHTTPHeaderField: "Authorization"), "Bearer new-token")
    }

    // MARK: Error mapping

    func testStatusCodesMapToErrors() async {
        let cases: [(Int, String, APIError)] = [
            (401, "{\"detail\": \"Not authenticated\"}", .unauthorized),
            (403, "{\"detail\": \"Requires role: qa\"}", .forbidden("Requires role: qa")),
            (404, "{\"detail\": \"Issue 9 not found\"}", .notFound("Issue 9 not found")),
            (409, "{\"detail\": \"Run is already completed\"}", .conflict("Run is already completed")),
            (422, "{\"detail\": \"Cannot move from Analyze to Closed\"}", .validation("Cannot move from Analyze to Closed")),
            (422, "{\"detail\": [{\"loc\": [\"body\", \"title\"], \"msg\": \"too short\"}]}", .validation("invalid input")),
            (500, "oops", .server(status: 500)),
        ]
        for (status, body, expected) in cases {
            transport.enqueue(status: status, json: body)
            await assertThrows(expected) { _ = try await self.client.getIssue(id: 9) }
        }
    }

    func testTransportFailureIsPassedThrough() async {
        transport.failure = APIError.transport("offline")
        await assertThrows(APIError.transport("offline")) { _ = try await self.client.getIssue(id: 1) }
    }

    // MARK: Transitions

    func testLegalTransitionIsSent() async throws {
        transport.enqueue(json: Fixtures.issueJSON)
        _ = try await client.transition(issueID: 7, from: .analyze, to: .integrate)
        XCTAssertEqual(transport.lastRequest.url?.path, "/api/issues/7/transition")
        XCTAssertEqual(transport.lastBodyJSON?["target"] as? String, "Integrate")
    }

    func testIllegalTransitionIsRejectedWithoutANetworkCall() async {
        await assertThrows(APIError.illegalTransition(from: .analyze, to: .closed)) {
            _ = try await self.client.transition(issueID: 7, from: .analyze, to: .closed)
        }
        XCTAssertTrue(transport.requests.isEmpty)
    }

    // MARK: Helper

    private func assertThrows(
        _ expected: APIError, file: StaticString = #filePath, line: UInt = #line,
        _ work: () async throws -> Void
    ) async {
        do {
            try await work()
            XCTFail("Expected \(expected) but nothing was thrown", file: file, line: line)
        } catch let error as APIError {
            XCTAssertEqual(error, expected, file: file, line: line)
        } catch {
            XCTFail("Unexpected error type: \(error)", file: file, line: line)
        }
    }
}
