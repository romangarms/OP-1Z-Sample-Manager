# Contribution Guidelines

Help on this project is always appreciated.

That said, we do have some guidelines.

## Creating issues

When creating issues, please fill out the template to the best of your ability. Some issues may not require every field, but please make sure your findings are expressed clearly.

- **Suggestions / missing features**: Explain in detail how you would like the feature to work and what problem it solves.
- **Bug reports**: Clearly describe the expected behavior and include steps to reproduce the bug so it can be tested.

## Assigning work

If there is an issue you would like to work on, we recommend leaving a comment describing your **intended approach** (not just an expression of interest). This helps maintainers quickly confirm that the plan aligns with the project’s vision and avoids duplicated effort.

For small, straightforward fixes (like those tagged `good first issue`), please skip the comment and open a pull request directly.

## Creating pull requests

Please open pull requests as drafts if they are not yet ready for review. Non-draft pull requests are assumed to be ready for review.

To create a pull request:
1. Fork this repository.
2. Make your changes in your fork.
3. Open a pull request to merge your changes back into this repo.

Please fill out the pull request template to the best of your ability.

If you want feedback or help on your pull request before it is finished, feel free to mark it as a draft and @mention one of the maintainers.

## Discussions

Have a question, idea, or problem that doesn’t warrant a GitHub issue?  
Please start a thread on our [discussions page](https://github.com/romangarms/OP-1Z-Sample-Manager/discussions) so the community and maintainers can respond publicly.

## Other (articles, posts, external links)

Writing an article about the project? Shared a post or video? Found an external resource mentioning it?

Feel free to [let us know](https://github.com/romangarms/OP-1Z-Sample-Manager/discussions), or email Roman at [romangarms@gmail.com](mailto:romangarms@gmail.com).

## Release signing (macOS)

Release builds of the macOS app are code-signed with a Developer ID certificate, notarized by Apple, and stapled so Gatekeeper opens them without warnings. This is done automatically by the `Build & Release` workflow when the following repository secrets are set. If they are missing (for example on pull requests from forks), the build still succeeds but the app is unsigned.

| Secret | Value |
| --- | --- |
| `MACOS_CERTIFICATE_P12` | Base64 of a `.p12` export of the **Developer ID Application** certificate and its private key |
| `MACOS_CERTIFICATE_PASSWORD` | Password chosen when exporting the `.p12` |
| `APPLE_ID` | Apple ID email of the developer account |
| `APPLE_TEAM_ID` | 10-character Team ID from <https://developer.apple.com/account> |
| `APPLE_APP_SPECIFIC_PASSWORD` | App-specific password generated at <https://account.apple.com> (Sign-In and Security → App-Specific Passwords) |

### One-time setup

1. Create a **Developer ID Application** certificate at <https://developer.apple.com/account/resources/certificates/add>. Generate the certificate signing request with Keychain Access (Certificate Assistant → Request a Certificate From a Certificate Authority, saved to disk) and upload it. Download the resulting `.cer` and double-click it so it lands in your login keychain next to its private key.
2. In Keychain Access, select the "Developer ID Application: …" certificate, expand it so the private key is included, right-click → Export, and save as `.p12` with a password.
3. Add the secrets:

   ```sh
   gh secret set MACOS_CERTIFICATE_P12 < <(base64 -i certificate.p12)
   gh secret set MACOS_CERTIFICATE_PASSWORD
   gh secret set APPLE_ID
   gh secret set APPLE_TEAM_ID
   gh secret set APPLE_APP_SPECIFIC_PASSWORD
   ```

4. Delete the local `.p12` file.

### Signing locally

`build.py` signs the app whenever `MACOS_CODESIGN_IDENTITY` is set to the name of an identity in your keychain, and notarizes it when the three `APPLE_*` variables are also set:

```sh
MACOS_CODESIGN_IDENTITY="Developer ID Application: Your Name (TEAMID)" python build.py
```

Hardened-runtime entitlements live in `entitlements.plist`. Pull request builds are signed but not notarized; only tagged releases are notarized.
