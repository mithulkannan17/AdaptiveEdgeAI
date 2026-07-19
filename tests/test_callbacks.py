from training.callbacks import EarlyStopping


def main():

    callback = EarlyStopping(

        patience=3,

        mode="min"

    )

    losses = [

        0.8,

        0.7,

        0.6,

        0.62,

        0.64,

        0.66,

        0.67

    ]

    for epoch, loss in enumerate(losses, start=1):

        stop = callback.step(loss)

        print(

            f"Epoch {epoch}"

            f" Loss={loss:.3f}"

            f" Stop={stop}"

        )

        if stop:

            print(

                "Early stopping triggered."

            )

            break


if __name__ == "__main__":

    main()