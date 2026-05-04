import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'

interface PrefSwitchProps {
  id: string
  label: string
  checked: boolean
  onChange: (next: boolean) => void
}

/** Label + Switch pair used across every settings tab for binary prefs. */
export function PrefSwitch({ id, label, checked, onChange }: PrefSwitchProps) {
  return (
    <div className="flex items-center justify-between">
      <Label htmlFor={id}>{label}</Label>
      <Switch id={id} checked={checked} onCheckedChange={onChange} />
    </div>
  )
}
