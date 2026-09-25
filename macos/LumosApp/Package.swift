// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "LumosApp",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "Lumos", targets: ["Lumos"]),
    ],
    targets: [
        .executableTarget(
            name: "Lumos",
            swiftSettings: [
                // `import Translation` otomatik (güçlü) bağlamasın; aşağıda zayıf bağlanır.
                .unsafeFlags(["-Xfrontend", "-disable-autolink-framework", "-Xfrontend", "Translation"]),
            ],
            linkerSettings: [
                // Translation.framework macOS 14.0–14.3'te yok (uygulama tabanı macOS 14);
                // kullanım @available(macOS 15) arkasında. build-app.sh otool ile doğrular.
                .unsafeFlags(["-Xlinker", "-weak_framework", "-Xlinker", "Translation"]),
            ]
        ),
    ]
)
