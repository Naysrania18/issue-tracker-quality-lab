// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "IssueTrackerClient",
    platforms: [.macOS(.v12), .iOS(.v15)],
    products: [
        .library(name: "IssueTrackerClient", targets: ["IssueTrackerClient"]),
        .executable(name: "issuetracker-cli", targets: ["issuetracker-cli"]),
    ],
    targets: [
        .target(name: "IssueTrackerClient"),
        .executableTarget(name: "issuetracker-cli", dependencies: ["IssueTrackerClient"]),
        .testTarget(name: "IssueTrackerClientTests", dependencies: ["IssueTrackerClient"]),
    ]
)
