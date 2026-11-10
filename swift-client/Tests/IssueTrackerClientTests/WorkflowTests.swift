import XCTest
@testable import IssueTrackerClient

final class WorkflowTests: XCTestCase {
    /// The same table the Python and Java suites use, written out so a change is easy to spot.
    private let legal: [IssueState: Set<IssueState>] = [
        .analyze: [.integrate],
        .integrate: [.build, .analyze],
        .build: [.verify, .integrate],
        .verify: [.closed, .analyze],
        .closed: [.analyze],
    ]

    func testEveryPairMatchesTheRules() {
        for from in IssueState.allCases {
            for target in IssueState.allCases {
                let expected = legal[from]?.contains(target) ?? false
                XCTAssertEqual(from.canMove(to: target), expected, "\(from) -> \(target)")
            }
        }
    }

    func testCannotCloseWithoutVerify() {
        for from in [IssueState.analyze, .integrate, .build] {
            XCTAssertFalse(from.canMove(to: .closed), "\(from) must not go straight to Closed")
        }
    }

    func testNoSelfTransitions() {
        for state in IssueState.allCases {
            XCTAssertFalse(state.canMove(to: state))
        }
    }

    func testRawValuesMatchTheServer() {
        XCTAssertEqual(IssueState.allCases.map { $0.rawValue }, ["Analyze", "Integrate", "Build", "Verify", "Closed"])
        XCTAssertEqual(Priority.allCases.map { $0.rawValue }, ["P1", "P2", "P3", "P4"])
    }

    func testNewIssueRoundTripsThroughJSON() throws {
        let original = NewIssue(title: "Round trip", component: "Mail", priority: .p4, expectedResult: "Works")
        let data = try JSONCoding.encoder().encode(original)
        let decoded = try JSONCoding.decoder().decode(NewIssue.self, from: data)
        XCTAssertEqual(decoded, original)
    }
}
