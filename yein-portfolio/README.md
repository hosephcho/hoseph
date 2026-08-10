# Yein Cho — Portfolio Website

예인이의 개인 포트폴리오 사이트예요. 대학 입학 지원 시 참고 자료로 쓸 수 있도록, 아래 세 가지 페이지로 구성되어 있어요.

- **About** (`/`) — 자기소개 페이지
- **Projects** (`/projects/`) — 학교 산출물 (Art / Essay / Other) 게시판
- **News Clips** (`/news/`) — 관심있게 본 뉴스 스크랩 게시판

콘텐츠는 [Decap CMS](https://decapcms.org)를 통해 `/admin/` 페이지에서 코딩 없이 사진과 글을 올릴 수 있어요.

## 기술 스택

- [Astro](https://astro.build) — 정적 사이트 생성
- [Decap CMS](https://decapcms.org) — 브라우저에서 글/사진 업로드 (Git 기반 CMS)
- [Netlify](https://netlify.com) — 무료 호스팅 + 자동 배포 + 로그인(Identity)

## 로컬 개발

```bash
cd yein-portfolio
npm install
npm run dev
```

`http://localhost:4321` 에서 확인할 수 있어요.

```bash
npm run build    # dist/ 에 정적 파일 생성
npm run preview  # 빌드 결과 미리보기
```

## 콘텐츠 구조

| 페이지 | 콘텐츠 경로 |
|---|---|
| About | `src/content/about/index.md` (파일 1개) |
| Projects | `src/content/projects/*.md` |
| News Clips | `src/content/news/*.md` |

각 마크다운 파일의 맨 위 `---` 사이 부분(frontmatter)에 제목·날짜·카테고리 등을 적고, 그 아래에 본문을 마크다운으로 작성해요. `/admin/`에서 글을 쓰면 이 형식으로 자동 생성돼요.

---

## Netlify 배포 및 CMS 설정 (최초 1회)

이 프로젝트는 하나의 GitHub 저장소(`hosephcho/hoseph`) 안의 `yein-portfolio/` 폴더에 있어요. Netlify에서 이 폴더만 사이트로 배포하도록 설정하면 돼요.

### 1. Netlify에 사이트 연결

1. [netlify.com](https://netlify.com) 무료 계정 생성 (GitHub 계정으로 로그인 가능)
2. **Add new site → Import an existing project → GitHub** 선택 후 `hosephcho/hoseph` 저장소 선택
3. 배포할 브랜치 선택 (예: `main`, 또는 현재 작업 브랜치)
4. Build 설정:
   - **Base directory**: `yein-portfolio`
   - **Build command**: `npm run build`
   - **Publish directory**: `dist` (Base directory 기준 상대 경로)
5. Deploy 클릭 → `https://[사이트이름].netlify.app` 주소가 생성돼요.

### 2. Netlify Identity + Git Gateway 활성화 (예인이가 로그인해서 글을 쓸 수 있도록)

1. Netlify 사이트 대시보드 → **Site configuration → Identity → Enable Identity**
2. **Registration**: `Invite only`로 설정 (아무나 가입 못하게)
3. Identity 설정에서 **Services → Git Gateway → Enable Git Gateway** 클릭
4. **Identity → Invite users** 에서 예인이 이메일 주소로 초대장 발송
5. 예인이가 이메일의 초대 링크를 클릭하면 비밀번호를 설정하고 로그인할 수 있어요

### 3. `/admin/config.yml` 브랜치 확인

`public/admin/config.yml`의 `backend.branch` 값이 Netlify에서 배포 중인 브랜치와 같은지 확인하세요. 다르면 아래처럼 수정 후 다시 push 해주세요.

```yaml
backend:
  name: git-gateway
  branch: main   # 실제 배포 브랜치 이름으로 변경
```

### 4. 글 올리기

배포가 끝나면 `https://[사이트이름].netlify.app/admin/` 로 접속 → 로그인 → 왼쪽 메뉴에서 **Projects** 또는 **News Clips** 선택 → **New Project** / **New News Clip** 버튼으로 사진과 글을 작성하면 자동으로 GitHub에 저장되고, Netlify가 자동으로 사이트를 다시 빌드해서 1~2분 내로 반영돼요.

---

## 커스텀 도메인 (선택)

Netlify 무료 플랜에서도 `Site configuration → Domain management`에서 개인 도메인을 연결할 수 있어요 (도메인 자체는 별도로 구매 필요, 도메인 없이 `netlify.app` 주소만 써도 충분해요).

## 색상 팔레트

"Lavender Blush" 팔레트를 사용했어요 (`src/styles/global.css`에 CSS 변수로 정의되어 있어요).

| 색상 | HEX |
|---|---|
| Lavender | `#C9BBEA` |
| Blush Pink | `#F6D4E4` |
| Cream (배경) | `#FFF8F2` |
| Ink (텍스트) | `#4A3B5C` |
