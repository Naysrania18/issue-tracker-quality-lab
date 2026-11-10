import Foundation
#if canImport(FoundationNetworking)
import FoundationNetworking   // URLSession lives here on Linux
#endif

/// The only thing the client needs from the network. Tests replace it with a mock, so no real
/// networking (and no UIKit/AppKit) is needed to test the client.
public protocol HTTPTransport: Sendable {
    func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse)
}

/// Real implementation on top of URLSession.
public struct URLSessionTransport: HTTPTransport {
    public init() {}

    public func send(_ request: URLRequest) async throws -> (Data, HTTPURLResponse) {
        try await withCheckedThrowingContinuation { continuation in
            let task = URLSession.shared.dataTask(with: request) { data, response, error in
                if let error = error {
                    continuation.resume(throwing: APIError.transport(error.localizedDescription))
                } else if let data = data, let http = response as? HTTPURLResponse {
                    continuation.resume(returning: (data, http))
                } else {
                    continuation.resume(throwing: APIError.transport("No response"))
                }
            }
            task.resume()
        }
    }
}
