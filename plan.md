# Aha! Catcher - Apple Watch Hand Gesture Detection Research

## Research Summary

### Available System-Level Gestures

**Double-Tap Gesture (Developer-Accessible)**
- **Availability**: watchOS 10.1+, Apple Watch Series 9, Ultra 2, and later models
- **Status**: ✅ Publicly available API for developers
- **Implementation**: SwiftUI `.handGestureShortcut()` modifier
- **Detection**: Uses accelerometer, gyroscope, and optical heart sensor with machine learning

### Recommended Approach: Double-Tap Gesture

The **double-tap gesture** is the only built-in, system-level gesture available to developers.

## Minimal Swift Code Implementation

### SwiftUI Implementation (watchOS 11+)

```swift
import SwiftUI

struct AhaCatcherView: View {
    @State private var ahaCount = 0
    @State private var lastAhaTime = Date()

    var body: some View {
        VStack(spacing: 20) {
            Text("Aha! Catcher")
                .font(.headline)

            Text("Ahas Caught: \(ahaCount)")
                .font(.title)

            Button {
                captureAhaMoment()
            } label: {
                Image(systemName: "lightbulb.fill")
                Text("Capture Aha!")
            }
            .handGestureShortcut(.primaryAction)  // Enable double-tap
            .buttonStyle(.borderedProminent)

            if ahaCount > 0 {
                Text("Last: \(lastAhaTime.formatted(date: .omitted, time: .shortened))")
                    .font(.caption)
                    .foregroundColor(.gray)
            }
        }
        .padding()
    }

    private func captureAhaMoment() {
        ahaCount += 1
        lastAhaTime = Date()

        // Provide haptic feedback
        WKInterfaceDevice.current().play(.success)

        // TODO: Save to persistent storage
        print("Aha moment captured at \(lastAhaTime)")
    }
}
```

### Key Features

1. **`.handGestureShortcut(.primaryAction)`**: Enables double-tap on the button
2. **Haptic Feedback**: Confirms the gesture was recognized
3. **Visual Feedback**: System automatically highlights the button outline
4. **Counter**: Tracks number of "Aha!" moments

### Requirements

- **Minimum watchOS**: 11.0 (for `.handGestureShortcut()`)
- **Device Support**: Apple Watch Series 9, Ultra 2, or later
- **Framework**: SwiftUI

### Alternative: Custom Gesture with CoreMotion

If you need more control or custom gestures:

```swift
import CoreMotion
import WatchKit

class GestureDetector {
    private let motionManager = CMMotionManager()
    private var lastShakeTime = Date()

    func startDetecting(onGesture: @escaping () -> Void) {
        guard motionManager.isDeviceMotionAvailable else { return }

        motionManager.deviceMotionUpdateInterval = 0.1
        motionManager.startDeviceMotionUpdates(to: .main) { motion, error in
            guard let motion = motion else { return }

            // Simple shake detection based on acceleration
            let acceleration = motion.userAcceleration
            let magnitude = sqrt(
                pow(acceleration.x, 2) +
                pow(acceleration.y, 2) +
                pow(acceleration.z, 2)
            )

            if magnitude > 2.5 {  // Threshold for shake
                let now = Date()
                if now.timeIntervalSince(self.lastShakeTime) > 1.0 {
                    self.lastShakeTime = now
                    onGesture()
                }
            }
        }
    }

    func stopDetecting() {
        motionManager.stopDeviceMotionUpdates()
    }
}
```

## Limitations

1. **Double-tap only**: Other hand gestures (clench, pinch) are not available to developers
2. **Device restrictions**: Requires newer Apple Watch models (Series 9+)
3. **watchOS version**: Needs watchOS 11+ for best SwiftUI integration
4. **Custom gestures**: Require CoreMotion and manual pattern recognition

---

## Data Transfer Architecture: Watch to Cloud API

### Overview

When the gesture is detected, the app needs to send the last 30 seconds of audio to a cloud API. There are two main architectural approaches:

### Approach 1: Direct Watch-to-Server Communication

**Architecture**: Watch → URLSession → Cloud API

The Apple Watch uses URLSession to send audio data directly to the cloud server.

#### How It Works
- If paired iPhone is connected: URLSession uses iPhone as a proxy (transparent to developer)
- If iPhone not available: Watch connects via known Wi-Fi networks
- watchOS automatically manages connection routing

#### Pros ✅
- **Simpler architecture**: Single codebase, no iPhone app required
- **Fewer points of failure**: Direct path reduces complexity
- **Automatic fallback**: System handles iPhone proxy transparently
- **Independent operation**: Works when iPhone is out of Bluetooth range (via Wi-Fi)
- **Lower latency**: No extra hop through iPhone app layer

#### Cons ❌
- **Battery drain**: Direct networking from Watch consumes more power
- **Reliability concerns**: Some developers report URLSession failures when iPhone unreachable
- **Limited background execution**: Watch apps have strict background time limits
- **Network constraints**: Watch has slower cellular/Wi-Fi than iPhone
- **File size limits**: Large audio files may timeout on Watch's limited connection
- **No iPhone fallback logic**: Can't leverage iPhone's better connectivity manually

**Best For**: Simple use cases, smaller payloads (<5MB), when iPhone is typically nearby

### Approach 2: iPhone as Intermediary

**Architecture**: Watch → WatchConnectivity → iPhone → URLSession → Cloud API

The Watch sends audio to iPhone companion app, which then uploads to the cloud.

#### How It Works
- Watch records audio and stores locally
- Uses WatchConnectivity framework to transfer file to iPhone
- iPhone app receives file and uploads via URLSession
- iPhone handles retry logic and background uploads

#### Pros ✅
- **Better reliability**: iPhone has superior network connectivity
- **Background uploads**: iOS supports proper background URLSession
- **Battery efficient**: Offloads heavy networking from Watch
- **Larger file support**: iPhone handles large files better
- **Retry logic**: Can implement sophisticated retry/queue mechanisms
- **Better error handling**: More resources for compression, encryption
- **Works offline**: Can queue uploads when no connectivity
- **Monitoring**: Easier to debug and monitor on iPhone

#### Cons ❌
- **Increased complexity**: Requires both Watch and iPhone apps
- **More code to maintain**: Two apps, WatchConnectivity setup
- **iPhone dependency**: Must be within Bluetooth range or on same Wi-Fi
- **Delayed uploads**: Transfer to iPhone adds latency
- **Data transfer limits**: WatchConnectivity has file size limits
- **Synchronization complexity**: Managing state across two devices

**Best For**: Production apps, larger files, reliable uploads, background processing

### Comparison Table

| Factor | Direct Watch-to-Server | iPhone Intermediary |
|--------|----------------------|-------------------|
| **Complexity** | Low | Medium-High |
| **Reliability** | Medium | High |
| **Battery Impact** | Higher | Lower (on Watch) |
| **File Size** | Limited (~5-10MB) | Larger files OK |
| **Background Upload** | Limited | Full support |
| **iPhone Required** | No (but helps) | Yes |
| **Development Time** | Faster | Slower |
| **Production Ready** | ⚠️ Conditional | ✅ Yes |

### Recommended Approach: **iPhone as Intermediary**

For the Aha! Catcher production app, **use iPhone as intermediary** because:

1. **30-second audio files** are 500KB-2MB (significant size)
2. **Reliability is critical** - users can't re-capture "Aha!" moments
3. **Background processing** - upload can continue even if user closes Watch app
4. **Better UX** - Watch app stays responsive, offloading heavy work
5. **Future-proof** - Easier to add features like audio processing, compression, metadata

### Audio Recording Strategy

**Continuous Buffer Recording**

To capture "last 30 seconds" when gesture detected, use a circular buffer:

```swift
// Continuously record in 30-second chunks
// When gesture detected, save current chunk + previous chunk
// Results in 30-60 seconds of audio (can trim to exact 30s)
```

**Recording Options**:

1. **WKAudioRecorderController** (Recommended for simplicity)
   - System UI, maximum duration control
   - `WKAudioRecorderControllerOptionsMaximumDurationKey: 30`
   - Limited customization

2. **AVAudioRecorder** (Recommended for control)
   - Direct access to audio buffer
   - Custom settings (format, quality, sample rate)
   - Can implement circular buffer for "last 30 seconds" capture
   - Requires "Privacy - Microphone Usage Description" in Info.plist

**Recommended Settings for Speech**:
- Format: AAC (kAudioFormatMPEG4AAC)
- Sample Rate: 16 kHz (WideBandSpeech preset)
- Bitrate: 32 kbps
- Estimated file size: ~1-1.5 MB for 30 seconds

### WatchConnectivity Implementation

**Data Transfer Method**: `transferFile(_:metadata:)`

This is the best choice because:
- Handles large files (audio recordings)
- Guaranteed delivery even if apps go to background
- Automatic retry if transfer fails
- System manages the queue

**Code Pattern**:

```swift
// Watch side
if WCSession.default.isReachable {
    WCSession.default.transferFile(audioURL, metadata: [
        "timestamp": Date(),
        "duration": 30.0
    ])
}

// iPhone side
func session(_ session: WCSession, didReceive file: WCSessionFile) {
    // Upload to cloud API
    uploadToCloud(fileURL: file.fileURL, metadata: file.metadata)
}
```

---

## Product Requirements Document (PRD)

### Product Vision

**Aha! Catcher** is an Apple Watch app that captures spontaneous moments of insight by recording the last 30 seconds of ambient audio when triggered by a simple hand gesture, enabling users to preserve and review their creative thoughts.

### Target Users

- **Knowledge Workers**: Professionals who have insights during meetings, commutes, or workouts
- **Students**: Learners who want to capture moments of understanding
- **Creatives**: Writers, designers, entrepreneurs with spontaneous ideas
- **Researchers**: People documenting thoughts and observations

### Core Value Proposition

"Never lose a brilliant idea again. Capture your 'Aha!' moments with a simple gesture—no need to fumble with your phone or remember to write it down later."

### User Stories

1. **As a user**, I want to capture the last 30 seconds of audio with a double-tap gesture, so I can preserve my spontaneous insights without interrupting my flow
2. **As a user**, I want my recordings automatically uploaded to the cloud, so I can access them later on any device
3. **As a user**, I want to receive haptic feedback when recording starts, so I know the gesture was recognized
4. **As a user**, I want to see a list of my captured "Aha!" moments, so I can review and organize my insights
5. **As a user**, I want the app to work offline, so I can capture moments even without connectivity
6. **As a user**, I want minimal battery drain, so the app doesn't impact my Watch's daily use

### Functional Requirements

#### Must Have (MVP)
1. **Gesture Detection**
   - Respond to double-tap gesture on Apple Watch Series 9+
   - Provide immediate haptic and visual feedback
   - Work when app is in foreground

2. **Audio Recording**
   - Continuously buffer last 30 seconds of audio
   - Save audio when gesture detected
   - Support standard audio formats (AAC preferred)
   - Include microphone permission handling

3. **Data Transfer**
   - Transfer recorded audio from Watch to iPhone
   - Use WatchConnectivity framework
   - Handle transfer failures gracefully
   - Queue recordings when iPhone unavailable

4. **Cloud Upload**
   - Upload recordings from iPhone to cloud API
   - Support background uploads
   - Retry failed uploads automatically
   - Handle authentication securely

5. **User Interface (Watch)**
   - Simple capture button as fallback to gesture
   - Show recording status
   - Display count of captured moments
   - Show last capture timestamp

6. **User Interface (iPhone)**
   - List of all captured recordings
   - Playback functionality
   - Upload status indicators
   - Settings panel

#### Should Have (V1.1)
- Transcription of audio recordings
- Search/filter captured moments
- Tags and categories
- Export recordings
- Sync across multiple devices
- Complication showing last capture

#### Could Have (Future)
- AI-powered insight summaries
- Integration with note-taking apps
- Sharing capabilities
- Voice commands to trigger capture
- Custom gesture patterns
- Real-time collaboration

### Non-Functional Requirements

1. **Performance**
   - Gesture detection latency: <500ms
   - Haptic feedback delay: <200ms
   - Audio processing: <2 seconds
   - Upload start time: <5 seconds (when connected)

2. **Reliability**
   - No lost recordings: 99.9% reliability
   - Offline queueing: 100% of recordings preserved
   - Upload success rate: >95% within 24 hours

3. **Battery Life**
   - Background recording impact: <5% per hour
   - Idle state impact: <1% per hour
   - Should not significantly impact daily Watch usage

4. **Privacy & Security**
   - All audio encrypted in transit (TLS)
   - Optional encryption at rest
   - User controls retention period
   - Clear privacy policy
   - Microphone permission required

5. **Compatibility**
   - watchOS: 11.0+
   - iOS: 17.0+
   - Apple Watch: Series 9, Ultra 2, or later
   - iPhone: Required as companion device

### Technical Constraints

- Maximum recording length: 30 seconds
- Audio format: AAC, 16kHz, 32kbps
- Maximum file size: ~1.5 MB per recording
- WatchConnectivity file transfer limit: 65 MB
- Background execution time limits apply

### Success Metrics

1. **Adoption**
   - Daily active users
   - Captures per user per day
   - User retention (7-day, 30-day)

2. **Quality**
   - Recording success rate
   - Upload success rate
   - Average time to upload
   - App crash rate

3. **Engagement**
   - Average captures per week
   - Playback rate (% of recordings played)
   - Settings customization rate

### Out of Scope (V1)

- Android/Wear OS support
- Older Apple Watch models (Series 8 and below)
- Video recording
- Real-time streaming
- Social features
- Third-party integrations (except cloud storage)

---

## Implementation Plan

### Phase 1: Foundation (Week 1-2)

#### 1.1 Project Setup
- [ ] Create Xcode project with Watch app target
- [ ] Add iOS companion app target
- [ ] Configure WatchConnectivity framework
- [ ] Set up project structure and architecture
- [ ] Configure Info.plist permissions (microphone)

#### 1.2 Basic Watch UI
- [ ] Create main SwiftUI view with capture button
- [ ] Implement double-tap gesture detection
- [ ] Add haptic feedback on gesture
- [ ] Design status indicators (recording, uploading)
- [ ] Add simple counter display

#### 1.3 Audio Foundation
- [ ] Implement AVAudioRecorder setup
- [ ] Configure audio session for watchOS
- [ ] Test basic recording functionality
- [ ] Implement permission request flow
- [ ] Handle microphone permission denial

### Phase 2: Audio Capture (Week 2-3)

#### 2.1 Continuous Recording Buffer
- [ ] Implement circular buffer for 30-second audio
- [ ] Set up audio recording parameters (AAC, 16kHz, 32kbps)
- [ ] Handle buffer overflow and memory management
- [ ] Test recording quality and file sizes
- [ ] Implement audio file management (temp storage)

#### 2.2 Gesture-Triggered Capture
- [ ] Wire gesture detection to audio capture
- [ ] Save last 30 seconds when gesture detected
- [ ] Generate unique filename with timestamp
- [ ] Store metadata (date, duration, location?)
- [ ] Implement local storage management

#### 2.3 Error Handling
- [ ] Handle recording failures gracefully
- [ ] Manage storage quota exceeded
- [ ] Add retry logic for failed recordings
- [ ] Log errors for debugging
- [ ] Show user-friendly error messages

### Phase 3: Watch-iPhone Communication (Week 3-4)

#### 3.1 WatchConnectivity Setup
- [ ] Initialize WCSession on both Watch and iPhone
- [ ] Implement session activation
- [ ] Handle session state changes
- [ ] Test session reachability
- [ ] Implement session delegate methods

#### 3.2 File Transfer Implementation
- [ ] Implement `transferFile()` on Watch side
- [ ] Implement `didReceive file:` on iPhone side
- [ ] Add metadata transfer (timestamp, duration)
- [ ] Handle transfer progress updates
- [ ] Implement transfer error handling

#### 3.3 Queue Management
- [ ] Queue recordings when iPhone unavailable
- [ ] Auto-retry transfers when connection restored
- [ ] Persist queue across app restarts
- [ ] Handle queue size limits
- [ ] Clean up transferred files

### Phase 4: Cloud Upload (Week 4-5)

#### 4.1 Network Layer
- [ ] Set up URLSession for uploads
- [ ] Implement background URLSession configuration
- [ ] Create API client for cloud service
- [ ] Implement authentication (API keys, OAuth)
- [ ] Add request/response models

#### 4.2 Upload Implementation
- [ ] Implement multipart file upload
- [ ] Add upload progress tracking
- [ ] Implement retry logic with exponential backoff
- [ ] Handle upload failures and timeouts
- [ ] Implement background upload tasks

#### 4.3 Offline Support
- [ ] Queue uploads when offline
- [ ] Detect network connectivity changes
- [ ] Auto-upload when connection restored
- [ ] Persist upload queue to disk
- [ ] Handle partial uploads/resume

### Phase 5: iPhone Companion App (Week 5-6)

#### 5.1 UI Implementation
- [ ] Create recordings list view
- [ ] Implement audio playback interface
- [ ] Add upload status indicators
- [ ] Design settings screen
- [ ] Implement pull-to-refresh

#### 5.2 Data Management
- [ ] Set up local database (Core Data or SwiftData)
- [ ] Implement data models for recordings
- [ ] Sync state between Watch and iPhone
- [ ] Handle file storage and cleanup
- [ ] Implement data persistence

#### 5.3 Playback & Management
- [ ] Implement AVAudioPlayer for playback
- [ ] Add playback controls (play, pause, scrub)
- [ ] Implement delete functionality
- [ ] Add bulk operations
- [ ] Implement search/filter

### Phase 6: Polish & Testing (Week 6-7)

#### 6.1 UI/UX Refinements
- [ ] Improve animations and transitions
- [ ] Add loading states and skeletons
- [ ] Optimize for different Watch sizes
- [ ] Test dark mode support
- [ ] Improve accessibility (VoiceOver)

#### 6.2 Testing
- [ ] Unit tests for core functionality
- [ ] Integration tests for WatchConnectivity
- [ ] Network tests (offline, slow connection)
- [ ] Battery usage testing
- [ ] Memory leak testing

#### 6.3 Performance Optimization
- [ ] Optimize audio buffer memory usage
- [ ] Reduce battery drain
- [ ] Optimize file transfer size (compression?)
- [ ] Improve app launch time
- [ ] Profile and fix performance bottlenecks

### Phase 7: Production Readiness (Week 7-8)

#### 7.1 Security & Privacy
- [ ] Implement end-to-end encryption (optional)
- [ ] Secure API credentials storage (Keychain)
- [ ] Add privacy policy screen
- [ ] Implement data deletion on user request
- [ ] Add analytics (privacy-respecting)

#### 7.2 Documentation
- [ ] Write README with setup instructions
- [ ] Document API integration
- [ ] Create user guide
- [ ] Write troubleshooting guide
- [ ] Document architecture decisions

#### 7.3 App Store Preparation
- [ ] Create app icons (Watch, iPhone, App Store)
- [ ] Write App Store description
- [ ] Create screenshots for all sizes
- [ ] Record demo video
- [ ] Prepare privacy policy
- [ ] Submit for TestFlight beta

---

## Technology Stack

### watchOS App
- **UI Framework**: SwiftUI
- **Audio Recording**: AVFoundation (AVAudioRecorder)
- **Gesture Detection**: SwiftUI `.handGestureShortcut()`
- **Data Transfer**: WatchConnectivity (WCSession)
- **Storage**: FileManager (temporary audio files)
- **Haptics**: WKInterfaceDevice

### iOS Companion App
- **UI Framework**: SwiftUI
- **Networking**: URLSession (background configuration)
- **Data Transfer**: WatchConnectivity (WCSession)
- **Persistence**: SwiftData or Core Data
- **Audio Playback**: AVFoundation (AVAudioPlayer)
- **Storage**: FileManager + app sandbox

### Cloud Infrastructure
- **API**: RESTful HTTP API (to be specified)
- **Storage**: Cloud object storage (S3, Google Cloud Storage, etc.)
- **Authentication**: API Key or OAuth 2.0
- **Format**: JSON for metadata, multipart/form-data for audio

### Development Tools
- **IDE**: Xcode 15+
- **Language**: Swift 5.9+
- **Version Control**: Git
- **CI/CD**: Xcode Cloud or GitHub Actions
- **Testing**: XCTest framework

---

## API Specification (Draft)

### Upload Endpoint

```
POST /api/v1/recordings

Headers:
- Authorization: Bearer <api_token>
- Content-Type: multipart/form-data

Body:
- audio_file: <binary audio data>
- metadata: {
    "timestamp": "2025-12-10T22:00:00Z",
    "duration": 30.0,
    "device_id": "watch_12345",
    "user_id": "user_67890"
  }

Response (200 OK):
{
  "id": "recording_abc123",
  "upload_url": "https://storage.example.com/...",
  "status": "uploaded",
  "created_at": "2025-12-10T22:00:05Z"
}

Response (4xx/5xx):
{
  "error": "error_code",
  "message": "Human-readable error message"
}
```

### List Recordings Endpoint

```
GET /api/v1/recordings?user_id=<user_id>&limit=50&offset=0

Headers:
- Authorization: Bearer <api_token>

Response (200 OK):
{
  "recordings": [
    {
      "id": "recording_abc123",
      "download_url": "https://storage.example.com/...",
      "timestamp": "2025-12-10T22:00:00Z",
      "duration": 30.0,
      "transcription": "..." (optional)
    }
  ],
  "total": 156,
  "limit": 50,
  "offset": 0
}
```

---

## Risk Assessment

### Technical Risks

1. **WatchConnectivity Reliability** (Medium)
   - Mitigation: Implement robust retry logic, queue management, persistence

2. **Battery Drain** (High)
   - Mitigation: Optimize recording buffer, use efficient audio codec, profile extensively

3. **Audio Quality** (Low)
   - Mitigation: Test various settings, allow user quality preferences

4. **Background Limitations** (Medium)
   - Mitigation: Use iPhone for heavy lifting, leverage background URLSession

### Product Risks

1. **User Adoption** (Medium)
   - Mitigation: Focus on UX, clear onboarding, demonstrate value quickly

2. **Privacy Concerns** (High)
   - Mitigation: Transparent privacy policy, user control, encryption options

3. **Limited Device Support** (Low)
   - Mitigation: Clearly communicate requirements, plan for older device support in V2

---

## Sources

### Gesture Detection
- [Enabling the double-tap gesture on Apple Watch](https://developer.apple.com/documentation/watchos-apps/enabling-double-tap)
- [Apple Watch double tap gesture announcement](https://www.apple.com/newsroom/2023/10/apple-watch-double-tap-gesture-now-available-with-watchos-10-1/)
- [WKGestureRecognizer Documentation](https://developer.apple.com/documentation/watchkit/wkgesturerecognizer)
- [Apple Developer Forums - AssistiveTouch API](https://developer.apple.com/forums/thread/702999)
- [CMMotionManager Documentation](https://developer.apple.com/documentation/coremotion/cmmotionmanager)
- [Gesture detection on Apple Watch - Medium](https://gstvdfnbch.medium.com/gesture-detection-on-the-apple-watch-core-motion-7650a652e5b9)

### Networking & Data Transfer
- [Transferring data with Watch Connectivity](https://developer.apple.com/documentation/watchconnectivity/transferring-data-with-watch-connectivity)
- [Watch Connectivity Documentation](https://developer.apple.com/documentation/watchconnectivity)
- [Data Synchronization Between iOS and watchOS - Medium](https://medium.com/@sheik25bareeth/data-synchronization-between-ios-and-watchos-using-watchconnectivity-009a3064e12a)
- [Three Ways to communicate via WatchConnectivity](https://alexanderweiss.dev/blog/2023-01-18-three-ways-to-communicate-via-watchconnectivity)
- [Apple Watch Data to Server - Forums](https://developer.apple.com/forums/thread/788402)
- [Making Network Requests on Apple Watch - O'Reilly](https://www.oreilly.com/library/view/developing-for-apple/9781680501940/f_0055.xhtml)

### Audio Recording
- [Audio Recording in watchOS Tutorial - Kodeco](https://www.kodeco.com/345-audio-recording-in-watchos-tutorial/page/2)
- [Creating a Watch App that Supports Audio Recording - Medium](https://medium.com/@ios_guru/creating-a-watch-app-that-supports-audio-recording-906af9806db0)
- [AVAudioRecorder Documentation](https://developer.apple.com/documentation/avfaudio/avaudiorecorder)
- [Recording audio on WatchOS - Stack Overflow](https://www.appsloveworld.com/swift/100/110/recording-audio-on-watchos-over-avaudiorecorder)
- [Using AVAudioRecorder with watchOS 4 - Forums](https://developer.apple.com/forums/thread/79932)
