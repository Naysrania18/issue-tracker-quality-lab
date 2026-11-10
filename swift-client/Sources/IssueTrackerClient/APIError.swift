import Foundation

/// Everything that can go wrong when talking to the tracker.
public enum APIError: Error, Equatable {
    case unauthorized                 // 401: missing or bad token
    case forbidden(String)            // 403: logged in but not allowed
    case notFound(String)             // 404
    case conflict(String)             // 409
    case validation(String)           // 422: the server rejected the input
    case server(status: Int)          // any other non-2xx answer
    case decoding                     // the body was not the JSON we expected
    case transport(String)            // no response at all (network down, bad URL...)
    case illegalTransition(from: IssueState, to: IssueState) // caught locally, never sent
}

extension APIError {
    /// Turn an HTTP status and body into the right error. FastAPI sends {"detail": "text"} for most errors
    /// and {"detail": [ ... ]} for input validation, so `detail` is read as text when possible.
    static func from(status: Int, body: Data) -> APIError {
        let detail = detailText(from: body)
        switch status {
        case 401: return .unauthorized
        case 403: return .forbidden(detail)
        case 404: return .notFound(detail)
        case 409: return .conflict(detail)
        case 422: return .validation(detail)
        default: return .server(status: status)
        }
    }

    private static func detailText(from body: Data) -> String {
        guard
            let object = try? JSONSerialization.jsonObject(with: body),
            let dict = object as? [String: Any]
        else { return "" }
        if let text = dict["detail"] as? String { return text }
        if dict["detail"] != nil { return "invalid input" }
        return ""
    }
}
