"use client";
import { z } from "zod";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { api } from "@/lib/api";
import { setToken } from "@/lib/auth";
import { useRouter } from "next/navigation";
import { useState } from "react";

const schema = z.object({
  username: z.string().min(3, "아이디/이메일을 입력하세요"),
  password: z.string().min(1, "비밀번호를 입력하세요"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const { register, handleSubmit, formState: { isSubmitting, errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { username: "", password: "" },
  });

  const onSubmit = async (values: FormData) => {
    setError(null);
    try {
      const res = await api.post("/auth/login", values);
      setToken(res.data.access_token);
      router.replace("/dashboard");
    } catch (e: any) {
      setError(e?.response?.data?.detail || "로그인에 실패했습니다");
    }
  };

  return (
    <div className="w-full max-w-md rounded-xl border bg-white p-6 shadow-sm">
      <h1 className="mb-4 text-xl font-semibold">로그인</h1>
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
        <div>
          <label className="block text-sm text-slate-600">이메일 또는 사용자명</label>
          <input
            type="text"
            className="mt-1 w-full rounded border px-3 py-2"
            {...register("username")}
          />
          {errors.username && (
            <p className="mt-1 text-sm text-red-600">{errors.username.message}</p>
          )}
        </div>
        <div>
          <label className="block text-sm text-slate-600">비밀번호</label>
          <input
            type="password"
            className="mt-1 w-full rounded border px-3 py-2"
            {...register("password")}
          />
          {errors.password && (
            <p className="mt-1 text-sm text-red-600">{errors.password.message}</p>
          )}
        </div>
        {error && <div className="text-sm text-red-600">{error}</div>}
        <button
          disabled={isSubmitting}
          className="w-full rounded bg-slate-900 px-4 py-2 text-white disabled:opacity-50"
        >
          {isSubmitting ? "로그인 중..." : "로그인"}
        </button>
      </form>
    </div>
  );
}
