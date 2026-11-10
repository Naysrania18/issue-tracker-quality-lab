import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking
#endif

/// Small async client for the demo issue tracker API.
public final class IssueTrackerClient {
    public let baseURL: URL
    public var token: String?
    private let transport: HTTPTransport

    public init(baseURL: URL, token: String? = nil, transport: HTTPTransport = URLSessionTransport()) {
        self.baseURL = baseURL
        self.token = token
        self.transport = transport
    }

    // MARK: - Public API

    /// Log in and remember the token for later calls.
    @discardableResult
    public func login(username: String, password: String) async throws -> String {
        struct Credentials: Encodable { let username: String; let password: String }
        struct TokenResponse: Decodable { let token: String }
        let response: TokenResponse = try await call(
            "POST", "/auth/login", body: Credentials(username: username, password: password))
        token = response.token
        return response.token
    }

    public func listIssues(text: String? = nil, state: IssueState? = nil, priority: Priority? = nil) async throws -> [Issue] {
        var query: [URLQueryItem] = []
        if let text = text, !text.isEmpty { query.append(URLQueryItem(name: "q", value: text)) }
        if let state = state { query.append(URLQueryItem(name: "state", value: state.rawValue)) }
        if let priority = priority { query.append(URLQueryItem(name: "priority", value: priority.rawValue)) }
        return try await call("GET", "/issues", query: query)
    }

    public func getIssue(id: Int) async throws -> Issue {
        try await call("GET", "/issues/\(id)")
    }

    public func createIssue(_ issue: NewIssue) async throws -> Issue {
        try await call("POST", "/issues", body: issue)
    }

    /// Move an issue to another workflow state. Illegal moves are rejected before any request is made.
    public func transition(issueID: Int, from current: IssueState, to target: IssueState) async throws -> Issue {
        guard current.canMove(to: target) else {
            throw APIError.illegalTransition(from: current, to: target)
        }
        struct Target: Encodable { let target: String }
        return try await call("POST", "/issues/\(issueID)/transition", body: Target(target: target.rawValue))
    }

    public func addComment(issueID: Int, body: String) async throws -> Comment {
        struct Body: Encodable { let body: String }
        return try await call("POST", "/issues/\(issueID)/comments", body: Body(body: body))
    }

    // MARK: - Plumbing

    /// Build the request. Kept separate (and internal) so tests can inspect exactly what would be sent.
    func makeRequest(method: String, path: String, query: [URLQueryItem] = [], bodyData: Data? = nil) throws -> URLRequest {
        guard var components = URLComponents(string: baseURL.absoluteString + path) else {
            throw APIError.transport("Bad URL: \(path)")
        }
        if !query.isEmpty { components.queryItems = query }
        guard let url = components.url else { throw APIError.transport("Bad URL: \(path)") }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        if let token = token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let bodyData = bodyData {
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
            request.httpBody = bodyData
        }
        return request
    }

    private func call<Response: Decodable>(
        _ method: String,
        _ path: String,
        query: [URLQueryItem] = [],
        body: (any Encodable)? = nil
    ) async throws -> Response {
        let bodyData = try body.map { try encode($0) }
        let request = try makeRequest(method: method, path: path, query: query, bodyData: bodyData)
        let (data, http) = try await transport.send(request)
        guard (200..<300).contains(http.statusCode) else {
            throw APIError.from(status: http.statusCode, body: data)
        }
        do {
            return try JSONCoding.decoder().decode(Response.self, from: data)
        } catch {
            throw APIError.decoding
        }
    }

    private func encode(_ value: any Encodable) throws -> Data {
        try JSONCoding.encoder().encode(AnyEncodable(value))
    }
}

/// Lets us encode "some Encodable" without making `call` generic over the body type as well.
private struct AnyEncodable: Encodable {
    private let encodeValue: (Encoder) throws -> Void
    init(_ value: any Encodable) { encodeValue = { try value.encode(to: $0) } }
    func encode(to encoder: Encoder) throws { try encodeValue(encoder) }
}
