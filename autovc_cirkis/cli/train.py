import argparse
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import yaml
from torch.utils.data.dataloader import DataLoader
from torch.utils.tensorboard import SummaryWriter
from tqdm.auto import trange

from autovc_cirkis.data import SpeakerDataset
from autovc_cirkis.modules.models import AutoVC


def main(
    config_path: Path,
    data_dir: Path,
    save_dir: Path,
    n_steps: int,
    save_steps: int,
    log_steps: int,
    batch_size: int,
    seg_len: int,
):
    torch.backends.cudnn.benchmark = True
    device = "cuda" if torch.cuda.is_available() else "cpu"
    save_dir.mkdir(exist_ok=True)
    config = yaml.load(config_path.open(mode="r"), Loader=yaml.FullLoader)
    writer = SummaryWriter(save_dir)

    model = AutoVC(config)
    model = torch.jit.script(model).to(device)
    train_set = SpeakerDataset(data_dir, seg_len=seg_len)
    data_loader = DataLoader(
        train_set,
        batch_size=batch_size,
        shuffle=True,
        num_workers=0,
        drop_last=True,
        worker_init_fn=lambda x: np.random.seed((torch.initial_seed()) % (2 ** 32)),
    )

    optimizer = torch.optim.Adam(
        filter(lambda p: p.requires_grad, model.parameters()), lr=1e-4
    )
    MSELoss = nn.MSELoss()
    L1Loss = nn.L1Loss()
    lambda_cnt = 1.0

    pbar = trange(n_steps)
    for step in pbar:
        try:
            mels, embs = next(data_iter)
        except:
            data_iter = iter(data_loader)
            mels, embs = next(data_iter)
        mels = mels.to(device)
        embs = embs.to(device)
        rec_org, rec_pst, codes = model(mels, embs)

        fb_codes = torch.cat(model.content_encoder(rec_pst, embs), dim=-1)

        # reconstruction loss
        org_loss = MSELoss(rec_org, mels)
        pst_loss = MSELoss(rec_pst, mels)
        # content consistency
        cnt_loss = L1Loss(fb_codes, codes)

        loss = org_loss + pst_loss + lambda_cnt * cnt_loss
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()

        if (step + 1) % save_steps == 0:
            model.save(save_dir / f"model-{step + 1}.pt")
            torch.save(optimizer.state_dict(), save_dir / f"optimizer-{step + 1}.pt")

        if (step + 1) % log_steps == 0:
            writer.add_scalar("loss/org_rec", org_loss.item(), step + 1)
            writer.add_scalar("loss/pst_rec", pst_loss.item(), step + 1)
            writer.add_scalar("loss/content", cnt_loss.item(), step + 1)
        pbar.set_postfix(
            {
                "org_rec": org_loss.item(),
                "pst_rec": pst_loss.item(),
                "cnt": cnt_loss.item(),
            }
        )


def cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("config_path", type=Path)
    parser.add_argument("data_dir", type=Path)
    parser.add_argument("save_dir", type=Path)
    parser.add_argument("--n_steps", type=int, default=int(1e7))
    parser.add_argument("--save_steps", type=int, default=10000)
    parser.add_argument("--log_steps", type=int, default=250)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--seg_len", type=int, default=128)
    main(**vars(parser.parse_args()))


if __name__ == "__main__":
    cli()
