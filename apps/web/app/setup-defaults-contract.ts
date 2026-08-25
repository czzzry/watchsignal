export type GenericSetupProfile = {
  id: string;
  label: string;
  order: number;
  avatarKey: string;
  colorKey: string;
};

export function createGenericSetupProfiles(): GenericSetupProfile[] {
  return [
    {
      id: "profile-1",
      label: "Viewer 1",
      order: 1,
      avatarKey: "spark",
      colorKey: "cyan",
    },
    {
      id: "profile-2",
      label: "Viewer 2",
      order: 2,
      avatarKey: "moon",
      colorKey: "rose",
    },
  ];
}
