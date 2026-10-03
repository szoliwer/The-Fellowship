import { createServerFn } from "@tanstack/react-start";
import { z } from "zod";

const signupSchema = z.object({
  firstName: z.string().trim().min(1, "Enter your first name.").max(80),
  username: z
    .string()
    .trim()
    .toLowerCase()
    .regex(/^[a-z0-9_]{3,30}$/, "Use 3–30 lowercase letters, numbers, or underscores."),
  password: z.string().min(8, "Use at least 8 characters.").max(72),
  location: z.string().trim().min(2, "Enter a city and state or region.").max(120),
});

export type SignupInput = z.infer<typeof signupSchema>;

export const createAccount = createServerFn({ method: "POST" })
  .inputValidator((data: SignupInput) => signupSchema.parse(data))
  .handler(async ({ data }) => {
    const { supabaseAdmin } = await import("@/integrations/supabase/client.server");
    const normalizedUsername = data.username.toLowerCase();
    const internalEmail = `${normalizedUsername}@members.thefellowship.local`;

    const { data: authData, error: authError } = await supabaseAdmin.auth.admin.createUser({
      email: internalEmail,
      password: data.password,
      email_confirm: true,
      user_metadata: { first_name: data.firstName, username: normalizedUsername },
    });

    if (authError || !authData.user) {
      if (authError?.message.toLowerCase().includes("already")) {
        throw new Error("That username is already taken.");
      }
      throw new Error("We couldn't create your account. Please try again.");
    }

    const { error: profileError } = await supabaseAdmin.from("profiles").insert({
      id: authData.user.id,
      first_name: data.firstName,
      username: normalizedUsername,
      location: data.location,
    });

    if (profileError) {
      await supabaseAdmin.auth.admin.deleteUser(authData.user.id);
      if (profileError.code === "23505") throw new Error("That username is already taken.");
      throw new Error("We couldn't save your profile. Please try again.");
    }

    return { firstName: data.firstName, username: normalizedUsername };
  });