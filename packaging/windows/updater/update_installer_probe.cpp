// Integration-test installer: prove the updater's parent has exited before
// touching any installed files. This executable is never shipped to users.
#include <windows.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>
int main(int argc, char **argv) {
  DWORD pid = 0;
  for (int i = 1; i < argc; ++i)
    if (strncmp(argv[i], "/UPDATEPID=", 11) == 0)
      pid = strtoul(argv[i] + 11, nullptr, 10);
  if (!pid) return 2;
  if (auto process = OpenProcess(SYNCHRONIZE, FALSE, pid)) {
    const auto status = WaitForSingleObject(process, 30000);
    CloseHandle(process);
    if (status != WAIT_OBJECT_0) return 3;
  }
  const auto path = std::getenv("CEDAR_TEST_INSTALL_MARKER");
  if (!path) return 4;
  FILE *file = fopen(path, "w");
  if (!file) return 5;
  fputs("Parent exited before installer continued.\n", file);
  fclose(file);
  return 0;
}
