import Foundation

/// P1 is a show stopper, P4 is minor.
public enum Priority: String, Codable, CaseIterable, Equatable {
    case p1 = "P1"
    case p2 = "P2"
    case p3 = "P3"
    case p4 = "P4"
}

/// The workflow: Analyze -> Integrate -> Build -> Verify -> Closed.
public enum IssueState: String, Codable, CaseIterable, Equatable {
    case analyze = "Analyze"
    case integrate = "Integrate"
    case build = "Build"
    case verify = "Verify"
    case closed = "Closed"

    /// Same rules as the server. Checking them here saves a network round trip for obvious mistakes.
    public func canMove(to target: IssueState) -> Bool {
        switch self {
        case .analyze: return target == .integrate
        case .integrate: return target == .build || target == .analyze
        case .build: return target == .verify || target == .integrate
        case .verify: return target == .closed || target == .analyze
        case .closed: return target == .analyze
        }
    }
}

/// An issue as returned by the API. JSON keys are snake_case; the decoder converts them (see JSONCoding).
public struct Issue: Codable, Equatable {
    public let id: Int
    public let title: String
    public let description: String
    public let stepsToReproduce: String
    public let expectedResult: String
    public let actualResult: String
    public let component: String
    public let priority: Priority
    public let state: IssueState
    public let reporter: String
    public let assignee: String?
    public let duplicateOf: Int?
    public let createdAt: String
    public let updatedAt: String
}

/// What you send to create an issue.
public struct NewIssue: Codable, Equatable {
    public var title: String
    public var component: String
    public var priority: Priority
    public var description: String
    public var stepsToReproduce: String
    public var expectedResult: String
    public var actualResult: String

    public init(
        title: String,
        component: String,
        priority: Priority = .p3,
        description: String = "",
        stepsToReproduce: String = "",
        expectedResult: String = "",
        actualResult: String = ""
    ) {
        self.title = title
        self.component = component
        self.priority = priority
        self.description = description
        self.stepsToReproduce = stepsToReproduce
        self.expectedResult = expectedResult
        self.actualResult = actualResult
    }
}

public struct Comment: Codable, Equatable {
    public let author: String
    public let body: String
    public let createdAt: String
}

/// Shared JSON settings: the API uses snake_case, Swift code uses camelCase.
enum JSONCoding {
    static func decoder() -> JSONDecoder {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }

    static func encoder() -> JSONEncoder {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }
}
