# ⚙️ ROSForge - Simplify ROS1 to ROS2 Migration

[![Download ROSForge](https://img.shields.io/badge/Download-ROSForge-brightgreen?style=for-the-badge)](https://github.com/ranvijay001/ROSForge/releases)

---

ROSForge is a command-line tool designed to help you move your robotics projects from ROS1 to ROS2. It uses AI models to analyze and fix your old robotics code, all with one simple command. This guide will help you download and run ROSForge on Windows, even if you don't have technical experience.

---

## 📋 What Does ROSForge Do?

ROSForge helps users:

- Move their existing ROS1 robotics packages to ROS2.
- Automatically analyze and update code using AI.
- Check the new code for errors after transformation.
- Use various AI models you bring in, like Claude, Gemini, or OpenAI.
- Work with common robotics programming tools like Python and C++.

---

## 🖥️ System Requirements

Before you download ROSForge, make sure your Windows computer meets these requirements:

- Windows 10 or newer (64-bit)
- At least 4 GB of RAM (8 GB recommended)
- 500 MB of free disk space for installation
- An active internet connection (needed during installation and AI model use)
- Basic command prompt access (comes with Windows by default)

This setup ensures ROSForge runs smoothly without interruptions.

---

## 🔧 Installing ROSForge on Windows

Follow these steps to get ROSForge running on your computer:

1. Open your web browser.

2. Go to the download page by clicking the badge below or visiting this link directly:

[![Download ROSForge](https://img.shields.io/badge/Download-ROSForge-brightgreen?style=for-the-badge)](https://github.com/ranvijay001/ROSForge/releases)

3. On the releases page, look for the latest Windows version. Check for files with `.exe` or `.zip` extensions.

4. Click the `.exe` file to download it directly. If you see a `.zip`, download it instead.

5. When the download finishes, open the file:

   - For `.exe` files, double-click to start the installer. Follow on-screen instructions, which usually only involve clicking “Next” and “Install.”
   - For `.zip` files, right-click and choose “Extract All,” then open the extracted folder.

6. After installation or extraction, find the ROSForge folder in your Start menu or on your Desktop.

7. Launch the Command Prompt in that folder by:

   - Holding the Shift key and right-clicking inside the folder.
   - Selecting “Open PowerShell window here” or “Open Command Prompt here.”

---

## 🚀 Running ROSForge

Once installed, running ROSForge is simple:

1. Open Command Prompt or PowerShell in the ROSForge folder.

2. Type the following command to see if ROSForge is ready:

```
rosforge --help
```

This command shows the list of commands and options you can use. It confirms the tool works.

3. To migrate a ROS1 package, use:

```
rosforge migrate <path_to_your_ROS1_package>
```

Replace `<path_to_your_ROS1_package>` with the actual folder location where your ROS1 code is stored.

Example:

```
rosforge migrate C:\Users\YourName\robotics\old_ros_package
```

4. ROSForge will analyze, transform, and validate your package. It may take a few minutes depending on your package size.

5. When complete, it will show a report with fixes and any remaining issues. You can then review and use the migrated ROS2 package.

---

## ⚙️ Using AI Models (BYOM Support)

ROSForge supports “Bring Your Own Model” (BYOM), which means you can connect AI models like Claude, Gemini, or OpenAI to improve migration results.

To use these:

1. Set up an account with your chosen AI provider.

2. Obtain an API key or token from their platform.

3. In ROSForge, add the model by running:

```
rosforge connect-model --provider <provider_name> --api-key <your_key>
```

Example:

```
rosforge connect-model --provider openai --api-key abc123xyz
```

4. After connection, ROSForge will use that model automatically during migration.

If no AI model is connected, ROSForge uses built-in defaults.

---

## 🛠️ Common Issues and Troubleshooting

If you run into problems, try these steps:

- Make sure your Windows is up to date.

- Check internet connection if AI models are not responding.

- Confirm you downloaded the latest ROSForge version.

- Run Command Prompt as Administrator if you get permission errors.

- Verify the path to your ROS1 package is correct.

- Consult the error messages shown by ROSForge for hints.

---

## 🗂️ How to Remove ROSForge

If you want to uninstall ROSForge:

- If you installed via `.exe`, go to “Apps & Features” in Windows settings, find ROSForge, and select “Uninstall.”

- If you used a `.zip` version, simply delete the ROSForge folder.

---

## 🔗 Resources and Links

Download the latest version here:

[![Download ROSForge](https://img.shields.io/badge/Download-ROSForge-brightgreen?style=for-the-badge)](https://github.com/ranvijay001/ROSForge/releases)

For more help and documentation, visit the same releases page or consult the README on GitHub.

---

## 📞 Getting Support

While ROSForge aims to be easy to use, you may want help:

- Check the GitHub issues page for questions.

- Look at online forums related to ROS migration.

- Review the help command anytime with:

```
rosforge --help
```

This shows all commands and options clearly.