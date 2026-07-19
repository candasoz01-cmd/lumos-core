// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "LumosApp",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "Lumos", targets: ["Lumos"]),
    ],
    targets: [
        .executableTarget(name: "Lumos"),
    ]
)
