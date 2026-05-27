import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { toast } from "sonner";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings · ICICI SIOS" }] }),
  component: SettingsPage,
});

function SettingsPage() {
  const [name, setName] = useState("Aarav Mehta");
  const [email, setEmail] = useState("aarav.mehta@icici.com");
  const [notifWeekly, setNotifWeekly] = useState(true);
  const [notifSignals, setNotifSignals] = useState(true);
  const [notifAssign, setNotifAssign] = useState(false);

  return (
    <>
      <PageHeader
        title="Settings"
        description="Manage your profile, team, integrations and notifications."
      />
      <Tabs defaultValue="profile" className="space-y-6">
        <TabsList>
          <TabsTrigger value="profile">Profile</TabsTrigger>
          <TabsTrigger value="notifications">Notifications</TabsTrigger>
          <TabsTrigger value="integrations">Integrations</TabsTrigger>
          <TabsTrigger value="team">Team</TabsTrigger>
        </TabsList>

        <TabsContent value="profile">
          <Section title="Profile">
            <div className="flex items-center gap-4 mb-6">
              <Avatar className="size-14">
                <AvatarFallback className="bg-primary text-primary-foreground">AM</AvatarFallback>
              </Avatar>
              <div>
                <div className="font-semibold">{name}</div>
                <div className="text-xs text-muted-foreground">Ventures Team · Admin</div>
              </div>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
              <Field label="Full name"><Input value={name} onChange={(e) => setName(e.target.value)} /></Field>
              <Field label="Email"><Input value={email} onChange={(e) => setEmail(e.target.value)} type="email" /></Field>
              <Field label="Team"><Input defaultValue="Ventures Team" /></Field>
              <Field label="Role"><Input defaultValue="Principal" /></Field>
            </div>
            <div className="mt-6">
              <Button onClick={() => toast.success("Profile updated")}>Save Changes</Button>
            </div>
          </Section>
        </TabsContent>

        <TabsContent value="notifications">
          <Section title="Notifications">
            <div className="divide-y divide-border max-w-2xl">
              <NotifRow
                label="Weekly intelligence digest"
                desc="Curated weekly summary of top startup signals."
                checked={notifWeekly}
                onChange={setNotifWeekly}
              />
              <NotifRow
                label="High-priority signals"
                desc="Get alerted when a tracked startup hits a key threshold."
                checked={notifSignals}
                onChange={setNotifSignals}
              />
              <NotifRow
                label="New assignments"
                desc="Email me when a startup is assigned to me."
                checked={notifAssign}
                onChange={setNotifAssign}
              />
            </div>
          </Section>
        </TabsContent>

        <TabsContent value="integrations">
          <Section title="Integrations">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-3xl">
              {[
                { name: "Crunchbase", status: "Connected" },
                { name: "Tracxn", status: "Connected" },
                { name: "Slack", status: "Connected" },
                { name: "Salesforce", status: "Not connected" },
                { name: "Microsoft Teams", status: "Not connected" },
                { name: "Looker", status: "Connected" },
              ].map((i) => (
                <div key={i.name} className="rounded-lg border border-border bg-card p-4 flex items-center justify-between">
                  <div>
                    <div className="font-medium text-sm">{i.name}</div>
                    <div className="text-xs text-muted-foreground">{i.status}</div>
                  </div>
                  <Button variant={i.status === "Connected" ? "outline" : "default"} size="sm">
                    {i.status === "Connected" ? "Manage" : "Connect"}
                  </Button>
                </div>
              ))}
            </div>
          </Section>
        </TabsContent>

        <TabsContent value="team">
          <Section title="Team Members">
            <div className="rounded-lg border border-border bg-card overflow-hidden max-w-3xl">
              {[
                { name: "Aarav Mehta", role: "Admin", team: "Ventures" },
                { name: "Priya Nair", role: "Analyst", team: "Innovation Lab" },
                { name: "Rohit Sen", role: "Analyst", team: "Digital Banking" },
                { name: "Kavya Iyer", role: "Lead", team: "Wealth Group" },
              ].map((m, idx) => (
                <div
                  key={m.name}
                  className={`flex items-center gap-3 p-4 ${idx > 0 ? "border-t border-border" : ""}`}
                >
                  <Avatar className="size-9">
                    <AvatarFallback className="bg-accent text-accent-foreground text-xs">
                      {m.name.split(" ").map((n) => n[0]).join("")}
                    </AvatarFallback>
                  </Avatar>
                  <div className="flex-1">
                    <div className="font-medium text-sm">{m.name}</div>
                    <div className="text-xs text-muted-foreground">{m.team}</div>
                  </div>
                  <div className="text-xs text-muted-foreground">{m.role}</div>
                </div>
              ))}
            </div>
          </Section>
        </TabsContent>
      </Tabs>
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card p-6 shadow-card">
      <h2 className="font-semibold mb-4">{title}</h2>
      {children}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label className="text-xs text-muted-foreground">{label}</Label>
      {children}
    </div>
  );
}

function NotifRow({
  label, desc, checked, onChange,
}: {
  label: string; desc: string; checked: boolean; onChange: (b: boolean) => void;
}) {
  return (
    <div className="flex items-center justify-between py-4">
      <div className="pr-6">
        <div className="font-medium text-sm">{label}</div>
        <div className="text-xs text-muted-foreground mt-0.5">{desc}</div>
      </div>
      <Switch checked={checked} onCheckedChange={onChange} />
    </div>
  );
}
