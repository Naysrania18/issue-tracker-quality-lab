import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif
@testable import IssueTrackerClient

/// Plays back canned responses and remembers every request, so tests can check what the client sent.
final class MockTransport: HTTPTransport, @unchecked Sendable {
    private var queue: [(status: Int, body: String)] = []
    private(set) var requests: [URLRequest] = []
    var failure: Error?

    func enqueue(status: Int = 200, json: String) {
        queue.append((status, json))
    }

    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        requests.append(request)
        if let failure = failure { throw failure }
        precondition(!queue.isEmpty, "Test forgot to enqueue a response")
        let next = queue.removeFirst()
        let response = HTTPURLResponse(
            url: request.url!, statusCode: next.status, httpVersion: nil, headerFields: nil)!
        return (Data(next.body.utf8), response)
    }

    var lastRequest: URLRequest { requests[requests.count - 1] }

    var lastBodyJSON: [String: Any]? {
        guard let data = lastRequest.httpBody else { return nil }
        return (try? JSONSerialization.jsonObject(with: data)) as? [String: Any]
    }
}

enum Fixtures {
    static let issueJSON = """
    {"id": 7, "title": "Sync hangs", "description": "Spinner never stops",
     "steps_to_reproduce": "1. Open mailbox", "expected_result": "Done", "actual_result": "Stuck",
     "component": "Mail > Sync", "priority": "P2", "assignee": null, "reporter": "rita",
     "state": "Analyze", "duplicate_of": null,
     "created_at": "2026-01-01T10:00:00+00:00", "updated_at": "2026-01-01T10:00:00+00:00"}
    """

    static func issuesJSON(_ count: Int) -> String {
        "[" + Array(repeating: issueJSON, count: count).joined(separator: ",") + "]"
    }
}
