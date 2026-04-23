import { useEffect } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { Badge } from "./ui/badge";
import { useEnvStore } from "@/state/environment";
import { useUserStore } from "@/state/user";

export default function EnvironmentSwitcher() {
  const { envs, current, load, switchEnv } = useEnvStore();
  const username = useUserStore((s) => s.username);
  useEffect(() => {
    if (username) load();
  }, [load, username]);
  return (
    <div className="flex items-center gap-2">
      <Select value={current?.name} onValueChange={switchEnv}>
        <SelectTrigger className="w-32">
          <SelectValue placeholder="Env" />
        </SelectTrigger>
        <SelectContent>
          {Object.entries(envs).map(([name, e]) => (
            <SelectItem value={name} key={name}>
              <span className="flex items-center gap-2">
                <Badge style={{ backgroundColor: e.color }} />
                {name}
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
